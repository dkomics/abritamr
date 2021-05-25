#!/usr/bin/env python3
import pathlib, pandas, math, sys,  re, logging
from abritamr.CustomLog import CustomFormatter

class Collate:

    """
    a base class for collation of amrfinder results - to be used when not doing MDU QC
    """
    

    REFGENES = pathlib.Path(__file__).parent / "db" / "refgenes_latest.csv"
    MATCH = ["ALLELEX", "BLASTX", "EXACTX", "POINTX"]
    NONRTM = [
        "Amikacin/Gentamicin/Kanamycin/Tobramycin",
        "Amikacin/Kanamycin",
        "Amikacin/Kanamycin/Tobramycin",
        "Amikacin/Quinolone",
        "Amikacin/Tobramycin",
        "Aminoglycosides",
        "Gentamicin",
        "Gentamicin/Kanamycin/Tobramycin",
        "Gentamicin/Tobramcyin",
        "Kanamycin",
        "Kanamycin/Tobramycin",
        "Spectinomycin",
        "Streptogramin",
        "Streptomycin",
        "Streptomycin/Spectinomycin",
        "Tobramycin",
    ]
    MACROLIDES = [
        "Erythromycin",
        "Erythromycin/Telithromycin",
        "Lincosamides",
        "Lincosamides/Streptogramin",
        "Macrolides",
        "Streptogramin",
    ]
    RTM = "Other aminoglycoside resistance (non-RMT)"
    MAC = "Macrolide, lincosamide and/or streptogramin resistance"
    
    # amr_data = Data(self.run_type, self.contigs, self.prefix)

    def __init__(self, args):
        self.logger =logging.getLogger(__name__) 
        self.logger.setLevel(logging.INFO)
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(CustomFormatter())
        fh = logging.FileHandler('abritamr.log')
        fh.setLevel(logging.INFO)
        formatter = logging.Formatter('[%(levelname)s:%(asctime)s] %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p') 
        fh.setFormatter(formatter)
        self.logger.addHandler(ch) 
        self.logger.addHandler(fh)
        self.prefix = args.prefix
        self.run_type = args.run_type
        self.input = args.input

    def joins(self, dict_for_joining):
        """
        make them a comma separated list
        """
        for i in dict_for_joining:
            if i != "Isolate":
                dict_for_joining[i] = list(set(dict_for_joining[i]))
                dict_for_joining[i] = ",".join(dict_for_joining[i])

        return dict_for_joining

    def get_drugclass(self, reftab, row, colname):

        """
        if the enhanced subclass is in either NONRTM or MACROLIDES then then use the groups specified by Norelle. If it is empty (-) then fall back on the AMRFinder subclass, else report the extended subclass
        """
        gene_id_col = "Gene symbol" if colname != "refseq_protein_accession" else "Accession of closest sequence"
        
        d = reftab[reftab[colname] == row[1][gene_id_col]]['enhanced_subclass'].values[0]
        if d in self.NONRTM:
            return self.RTM
        elif d in self.MACROLIDES:
            return self.MAC
        elif d == "-":
            return reftab[reftab[colname] == row[1]["Gene symbol"]][
                "subclass"
            ].unique()[0]
        else:
            return d

    def extract_bifunctional_name(self, protein, reftab):
        """
        extract the joint name of bifunctional genes
        """
        return reftab[reftab["refseq_protein_accession"] == protein]["gene_family"].values[0]

    def extract_gene_name(self, protein, reftab):

        if reftab[reftab["refseq_protein_accession"] == protein]["allele"].values[0] != '-':
            return reftab[reftab["refseq_protein_accession"] == protein]["allele"].values[0]
        else:
            return reftab[reftab["refseq_protein_accession"] == protein]["gene_family"].values[0]
            
    def setup_dict(self, drugclass_dict, reftab, row):
        """
        return the dictionary for collation
        """
        
        if row[1]["Gene symbol"] in list(reftab["allele"]):
            drugclass = self.get_drugclass(
                    reftab=reftab, row=row, colname="allele"
                    )
            drugname = self.extract_gene_name(protein = row[1]["Accession of closest sequence"], reftab = reftab)

        elif row[1]["Gene symbol"] in list(reftab["gene_family"]):
            drugclass = self.get_drugclass(
                reftab=reftab, row=row, colname="refseq_protein_accession"
            )
            drugname = f"{self.extract_gene_name(protein = row[1]['Accession of closest sequence'], reftab = reftab)}*" if not row[1]["Method"] in ["EXACTX", "ALLELEX", "POINTX"] else f"{self.extract_gene_name(protein = row[1]['Accession of closest sequence'], reftab = reftab)}"
            
        elif row[1]["Accession of closest sequence"] in list(reftab["refseq_protein_accession"]):
            drugclass = self.get_drugclass(
                reftab = reftab, row = row, colname = "refseq_protein_accession"
            )
            drugname = self.extract_bifunctional_name(protein = row[1]['Accession of closest sequence'], reftab = reftab)
        else:
            drugname = row[1]["Gene symbol"]
            drugclass = "Unknown"

        if drugclass in drugclass_dict:
            drugclass_dict[drugclass].append(drugname)
        elif drugclass not in drugclass_dict:
            drugclass_dict[drugclass] = [drugname]

        return drugclass_dict

    def _virulence_dict(self, virulence_dict, row):
        """
        report virulence factors
        """
        if row[1]['Element subtype'] in virulence_dict:
            virulence_dict[row[1]['Element subtype']].append(row[1]['Gene symbol'])
        else:
            virulence_dict[row[1]['Element subtype']] = [row[1]['Gene symbol']]
        return virulence_dict

    def get_per_isolate(self, reftab, df, isolate):
        """
        make three dictionaries for each isolate that contain the drug class assignments for each match that is one of ALLELEX,POINTX, EXACTX or BLASTX, another dictionary which lists all partial mathces and a dictionary of virulence factors
        """
        drugclass_dict = {"Isolate": isolate}
        partials = {"Isolate": isolate}
        virulence = {"Isolate": isolate}
        for row in df.iterrows():
            # print(row)
            # if the match is good then generate a drugclass dict
            if row[1]["Gene symbol"] == "aac(6')-Ib-cr" and row[1]["Method"] in ["EXACTX", "ALLELEX"]: # This is always a partial - unclear
                partials = self.setup_dict(drugclass_dict = partials, reftab = reftab, row = row)
            elif row[1]["Method"] in self.MATCH and row[1]["Scope"] == "core" and row[1]["Element type"] == "AMR":
                drugclass_dict = self.setup_dict(drugclass_dict = drugclass_dict, reftab = reftab, row = row)
            elif row[1]["Method"] not in self.MATCH and row[1]["Scope"] == "core" and row[1]["Element type"] == "AMR":
                partials = self.setup_dict(drugclass_dict = partials, reftab = reftab, row = row)
            elif row[1]["Method"] in self.MATCH and row[1]['Element type'] == 'VIRULENCE':
                virulence = self._virulence_dict(virulence_dict = virulence, row = row)
        drugclass_dict = self.joins(dict_for_joining=drugclass_dict)
        partials = self.joins(dict_for_joining=partials)
        virulence = self.joins(dict_for_joining = virulence)
        return drugclass_dict, partials, virulence

    
    def save_files(self, path, match, partial, virulence):
        
        files = {'summary_matches.txt': match, 'summary_partials.txt': partial, 'summary_virulence.txt':virulence}
        for f in files:
            out = f"{path}/{f}" if path != '' else f"{f}"
            self.logger.info(f"Saving {out}")
            files[f].set_index('Isolate').to_csv(f"{out}", sep = '\t')
        return True
        

    def _get_reftab(self):
        """
        get reftab
        """

        reftab = pandas.read_csv(self.REFGENES)
        reftab = reftab.fillna("-")

        return reftab

    def collate(self, prefix = ''):
        """
        if the refgenes.csv is present then proceed to collate data and save the csv files.
        """

        
        reftab = self._get_reftab()
        
        df = pandas.read_csv(f"{prefix}/amrfinder.out", sep="\t")
        self.logger.info(f"Opened amrfinder output for {prefix}")
        drug, partial, virulence = self.get_per_isolate(
            reftab=reftab, df=df, isolate=prefix
        )
        
        summary_drugs = pandas.DataFrame(drug, index = [0])
        summary_partial = pandas.DataFrame(partial, index = [0])
        summary_virulence = pandas.DataFrame(virulence, index = [0])
        return summary_drugs, summary_partial,summary_virulence
        
    
    def _combine_df(self, existing, temp):
        """
        combine result dataframes for batch
        """
        if existing.empty:
            existing = temp
        else:
            existing = existing.append(temp)
        
        return existing

    def _batch_collate(self,input_file):


        summary_matches = pandas.DataFrame()
        summary_partial = pandas.DataFrame()
        summary_virulence = pandas.DataFrame()

        df = pandas.read_csv(input_file, sep = '\t', header = None)
        for row in df.iterrows():
            prefix = f"{row[1][0]}"
            self.logger.info(f"Collating results for {prefix}")
            temp_match, temp_partial, temp_virulence = self.collate(prefix = prefix)
            summary_matches = self._combine_df(existing = summary_matches, temp = temp_match)
            summary_partial = self._combine_df(existing = summary_partial, temp = temp_partial)
            summary_virulence = self._combine_df(existing = summary_virulence, temp = temp_virulence)
        
        return summary_matches, summary_partial, summary_virulence

    def run(self):


        if not pathlib.Path(self.REFGENES).exists():
            self.logger.critical(f"The refgenes DB ({self.REFGENES}) seems to be missing.")
            raise SystemExit

        if self.run_type != 'batch':
            self.logger.info(f"This is a single sample run.")
            summary_drugs, summary_partial, virulence = self.collate(prefix = self.prefix)
        else:
            self.logger.info(f"You are running abritamr in batch mode. Your collated results will be saved.")
            summary_drugs, summary_partial, virulence = self._batch_collate(input_file = self.input)
        self.logger.info(f"Saving files now.")
        self.save_files(path='' if self.run_type == 'batch' else f"{self.prefix}", match = summary_drugs,partial=summary_partial, virulence = virulence)
        
class MduCollate(Collate):
    def __init__(self, args):
        self.logger =logging.getLogger(__name__) 
        self.logger.setLevel(logging.INFO)
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(CustomFormatter())
        fh = logging.FileHandler('abritamr.log')
        fh.setLevel(logging.INFO)
        formatter = logging.Formatter('[%(levelname)s:%(asctime)s] %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p') 
        fh.setFormatter(formatter)
        self.logger.addHandler(ch) 
        self.logger.addHandler(fh)

        self.mduqc = args.qc
        self.db = args.db
        self.partials = args.partials
        self.match = args.matches
        self.runid = args.runid
        self.NONE_CODES = {
            "Salmonella":"CPase_ESBL_AmpC_16S_NEG",
            "Shigella":"CPase_ESBL_AmpC_16S_NEG",
            "Staphylococcus":"Mec_VanAB_Linez_NEG",
            "Enterococcus":"Van_Linez_NEG",
            "Other":"Cpase_16S_mcr_NEG"
        }

    def mdu_qc_tab(self):
        self.logger.info(f"Checking the format of the QC file")
        cols = ["ISOLATE", 'SPECIES_EXP', 'SPECIES_OBS', 'TEST_QC']
        tab = pandas.read_csv(self.mduqc)
        tab = tab.rename(columns = {tab.columns[0]: 'ISOLATE'})
        for c in cols:
            if c not in list(tab.columns):
                self.logger.critical(f"There seems to be a problem with your QC file. This file must have {','.join(cols)}. Please check your input and try again.")
                raise SystemExit

        pos = pandas.DataFrame(data = {"ISOLATE": "9999-99888", "TEST_QC" : "PASS", "SPECIES_EXP":"Staphylococcus aureus", "SPECIES_OBS":"Staphylococcus aureus" }, index = [0])
        
        return tab.append(pos)

    def strip_bla(self, gene):
        '''
        strip bla from front of genes except
        '''
        if gene.startswith("bla") and len(gene) >6 and gene.endswith("*"):
            gene = gene.replace("bla", "")
        elif gene.startswith("bla") and len(gene) >5 and not gene.endswith("*"):
            gene = gene.replace("bla", "")
        return gene

    def get_passed_isolates(self, qc_tab):
        """
        generate lists of isolates that passed QC and need AMR, failed QC and should have AMR and all other isolates
        """        
        failed = list(
            qc_tab[qc_tab["TEST_QC"] == False]["ISOLATE"]
        )  # isolates that failed qc and should have amr
        passed = list(
            qc_tab[qc_tab["TEST_QC"] == True]["ISOLATE"]
        )  

        return (passed, failed)


    # Carbapenemase to be reported for all cases
    # Carbapenemase (MBL) all in all HOWEVER if blaL1 should  not be reported in Stenotrophomonas maltophilia
    # Carbapenemase (OXA-51 family) REPORTED IN ALL except in Acinetobacter baumannii,Acinetobacter calcoaceticus,Acinetobacter nosocomialis,Acinetobacter pittii,Acinetobacter baumannii complex,
    # All ESBL in Salmonella and Shigella
    # ESBL (Amp C type) in Salmonella and Shigella
    # Aminoglycosides (Ribosomal methyltransferases) ALL
    # Colistin ALL
    # Oxazolidinone & phenicol resistance if Genus = Enterococcus or Staphylococcus aureus and Staphylococcus argenteus
    # report vanA*, B*, C*, vanD*, vanE*, vanG*, vanL*, vanM*, vanN* 
    # Methicillin ALL

    def get_all_genes(self, row):
        all_genes = []
        for r in row[1]:
            if isinstance(r, str):
                if len(r.split(",")) > 1:
                    for a in r.split(","):
                        all_genes.append(a)
                else:
                    all_genes.append(r)
        return all_genes

    def none_replacement_code(self, genus):

        if genus in self.NONE_CODES:
            return self.NONE_CODES[genus]
        else:
            return "GENRL_AMR_NEG1"


    def reporting_logic(self, row, species, neg_code = True):
        # get all genes found
        all_genes = self.get_all_genes(row)
        isodict = row[1].to_dict()
        # determine the genus EXPECTED
        genus = species.split()[0]
        reportable = [
            "Carbapenemase",
            "Carbapenemase (MBL)",
            "Carbapenemase (OXA-51 family)",
            "ESBL",
            "ESBL (AmpC type)",
            "Aminoglycosides (Ribosomal methyltransferase)",
            "Colistin",
            "Oxazolidinone & phenicol resistance",
            "Vancomycin",
            "Methicillin"
        ]
        non_caveat_reportable = [
            "Carbapenemase",
            "Aminoglycosides (Ribosomal methyltransferase)",
            "Colistin"
        ]

        abacter_excluded = [
            "Acinetobacter baumannii",
            "Acinetobacter calcoaceticus",
            "Acinetobacter nosocomialis",
            "Acinetobacter pittii",
            "Acinetobacter baumannii complex"
        ]

        
        van_match = re.compile("van[A,B,C,D,E,G,L,M,N][\S]*")
        mec_match = re.compile("mec[^IR]")
        
        genes_reported = []  # genes for reporting
        genes_not_reported = []  # genes found but not reportable
        for i in isodict:
            genes = []
            if isinstance(isodict[i], str):
                genes = isodict[i].split(',')
            if genes != []: # for each bin we do things to genes
                if i in reportable:
                    if i in non_caveat_reportable:
                        genes_reported.extend(genes)
                    elif i == "Carbapenemase (MBL)" and species != "Stenotrophomonas maltophilia":
                        genes_reported.extend(genes)
                    elif i == "Carbapenemase (MBL)" and species == "Stenotrophomonas maltophilia":
                         # if species is "Stenotrophomonas maltophilia" don't report blaL1
                        genes_reported.extend([g for g in genes if not g.startswith("blaL1")])
                        genes_not_reported.extend([g for g in genes if g.startswith("blaL1")])
                    elif i == "Carbapenemase (OXA-51 family)" and species not in abacter_excluded:
                        genes_reported.extend(genes)
                    elif i in ["ESBL","ESBL (AmpC type)"] and genus in ["Salmonella"]: 
                        genes_reported.extend(genes)
                    elif i in ["ESBL","ESBL (AmpC type)"] and genus in ["Shigella"]: 
                        genes_reported.extend([g for g in genes if "blaEC" not in g])
                        genes_not_reported.extend([g for g in genes if "blaEC" in g]) # don't report blaEC for shigella
                    elif i == "Oxazolidinone & phenicol resistance":
                        if species in ["Staphylococcus aureus","Staphylococcus argenteus"] or genus == "Enterococcus":
                            genes_reported.extend(genes)
                        else:
                            genes_not_reported.extend(genes)
                    elif i == "Vancomycin":
                        genes_reported.extend([g for g in genes if van_match.match(g)])
                        genes_not_reported.extend([g for g in genes if not van_match.match(g)])
                    elif i == "Methicillin":
                        genes_reported.extend([g for g in genes if mec_match.match(g)])
                        genes_not_reported.extend([g for g in genes if not mec_match.match(g)])
                    else:
                        genes_not_reported.extend(genes)

                else:
                    genes_not_reported.extend(genes)
        if genes_reported == []:
            genes_reported = [self.none_replacement_code(genus= genus)] if neg_code else ''
        if genes_not_reported == []:
            genes_not_reported = ["No non-reportable genes found."] if neg_code else ''
            # break
        
        self.logger.info(f"{row[1]['Isolate']} has {len(genes_reported)} reportable genes.")
        return genes_reported, genes_not_reported


    def assign_itemcode(self,mduid, reg):
        self.logger.info(f"Checking for item code")
        m = reg.match(mduid)
        try:
            itemcode = m.group('itemcode') if m.group('itemcode') else ''
        except AttributeError:
            itemcode = ''
        return itemcode

    def assign_mduid(self, mduid, reg):
        self.logger.info(f"Extracting MDU sample ID")
        m = reg.match(mduid)
        try:
            mduid = m.group('id')
        except AttributeError:
            mduid = mduid.split('/')[-1]
        return mduid

    def mdu_reporting(self, match, neg_code = True):

        self.logger.info(f"Applying MDU business logic {'matches' if neg_code else 'partials'}.")
        mduidreg = re.compile(r'(?P<id>[0-9]{4}-[0-9]{5,6})-?(?P<itemcode>.{1,2})?')
        reporting_df = pandas.DataFrame()
        qc = self.mdu_qc_tab()
        match_df = pandas.read_csv(match, sep = '\t')
        for row in match_df.iterrows():
            isolate = row[1]['Isolate']
            item_code = self.assign_itemcode(isolate, mduidreg)
            md = self.assign_mduid(isolate, mduidreg)
            d = {"MDU sample ID": md, "Item code" : item_code}
            qcdf = qc[qc['ISOLATE'].str.contains(isolate)]
            exp_species = qcdf["SPECIES_EXP"].values[0]
            obs_species = qcdf["SPECIES_OBS"].values[0]
           
            species = obs_species if obs_species == exp_species else exp_species
            genes_reported, genes_not_reported = self.reporting_logic(
                row=row, species=species, neg_code=neg_code
            )
            # strip bla
            genes_not_reported = [self.strip_bla(g) for g in genes_not_reported]
            genes_reported = [self.strip_bla(g) for g in genes_reported]
            d["Resistance genes (alleles) detected"] = ",".join(genes_reported)
            d["Resistance genes (alleles) det (non-rpt)"] = ",".join(genes_not_reported)
            if qcdf["TEST_QC"].values[0] == 'FAIL': # species not needed for MDU LIMS upload
                d["Species_exp"] = exp_species
            d["Species_obs"] = obs_species
            d["Species_exp"] = exp_species
            d['db_version'] = self.db
            tempdf = pandas.DataFrame(d, index=[0])
            tempdf = tempdf.set_index("MDU sample ID")
            # print(tempdf)
            if reporting_df.empty:
                reporting_df = tempdf
            else:
                reporting_df = reporting_df.append(tempdf)
        
        return reporting_df.reindex(labels = ['Item code','Resistance genes (alleles) detected','Resistance genes (alleles) det (non-rpt)','Species_obs', 'Species_exp', 'db_version'], axis = 'columns')

    
    def save_spreadsheet(
        self,
        passed_match,
        passed_partials,
        
    ):
        writer = pandas.ExcelWriter(f"{self.runid}_MMS118.xlsx", engine="xlsxwriter")
        passed_match.to_excel(writer, sheet_name="MMS118")
        passed_partials.to_excel(writer, sheet_name="Passed QC partial")
        writer.close()

    def run(self):

        passed_match_df = self.mdu_reporting(match=self.match)
        passed_partials_df = self.mdu_reporting(match = self.partials, neg_code=False)
        self.save_spreadsheet(
            passed_match_df,
            passed_partials_df,

        )
