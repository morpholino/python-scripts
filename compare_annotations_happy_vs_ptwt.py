import os
from Bio import SeqIO
import time

#IMPORTANT BUG - when looking for flanking polymorphisms, SNPs of neighbouring genes may be 
#falsely included as intra-CDS!
#code rewritten but not tested

homedir = "/Users/zoliq/ownCloud/"
#homedir = "/Volumes/zoliq data/ownCloud/"
wd = homedir + "genomes/phatr/happy phatr"
os.chdir(wd)
datatable = "Phatr3_variant_mapping_geneious.tsv"
prevtargets = "hp-targets.tsv"
errorname = "compare_annotations_errors.txt"

fastafile = SeqIO.parse("db/Phaeodactylum_tricornutum.ASM15095v2.cds.all.fa", "fasta")
fastafile2 = SeqIO.parse("db/Phaeodactylum_tricornutum.ASM15095v2.cdna.all.fa", "fasta")

gencode = {
    'ATA':'I', 'ATC':'I', 'ATT':'I', 'ATG':'M',
    'ACA':'T', 'ACC':'T', 'ACG':'T', 'ACT':'T',
    'AAC':'N', 'AAT':'N', 'AAA':'K', 'AAG':'K',
    'AGC':'S', 'AGT':'S', 'AGA':'R', 'AGG':'R',
    'CTA':'L', 'CTC':'L', 'CTG':'L', 'CTT':'L',
    'CCA':'P', 'CCC':'P', 'CCG':'P', 'CCT':'P',
    'CAC':'H', 'CAT':'H', 'CAA':'Q', 'CAG':'Q',
    'CGA':'R', 'CGC':'R', 'CGG':'R', 'CGT':'R',
    'GTA':'V', 'GTC':'V', 'GTG':'V', 'GTT':'V',
    'GCA':'A', 'GCC':'A', 'GCG':'A', 'GCT':'A',
    'GAC':'D', 'GAT':'D', 'GAA':'E', 'GAG':'E',
    'GGA':'G', 'GGC':'G', 'GGG':'G', 'GGT':'G',
    'TCA':'S', 'TCC':'S', 'TCG':'S', 'TCT':'S',
    'TTC':'F', 'TTT':'F', 'TTA':'L', 'TTG':'L',
    'TAC':'Y', 'TAT':'Y', 'TAA':'X', 'TAG':'X',
    'TGC':'C', 'TGT':'C', 'TGA':'X', 'TGG':'W'}

def translation(sequence):
    cut_seq = []
    for i in range(0,len(sequence)-2,3):
        cut_seq.append(sequence[i:i+3])
    aa = []
    for codon in cut_seq:
        if 'N' in codon:
            aa.append('X')
        else:
            aa.append(gencode[str(codon)]) #with the str() here also runs with python2.7
    return ''.join(aa)


def overlaps(moduleA, moduleB):
	startA = moduleA[0]
	endA = moduleA[1]
	startB = moduleB[0]
	endB = moduleB[1]
	if startA <= startB <= endA:
		if startA <= endB <= endA:
			overlap = "embed"
		else:
			overlap = "overlap"
	elif startA <= endB <= endA:
		overlap = "overlap"
	elif startB <= startA <= endB and startB <= startB <= endB:
		overlap = "embed"
	else:
		overlap = "none"
	return overlap

def decor(string):
	def wrap():
		print("===============")
		print(string)
		print("===============")
	return wrap


##############################
###          MAIN          ###
##############################

with open(prevtargets) as f:
	targets = f.read().split("\n")
targets_d = {}
for l in targets:
	line = l.split("\t")
	if len(line) > 1:
		for t in line[1].split(";"):
			targets_d[t] = line[0]

with open(datatable) as f:
	data = f.read().split("\n")
	if data[0].startswith("gene_id"):
		data = data[1:]

errorfile = open(errorname, "w")
reporterrors = False
"""
the table includes the following info:
gene_id	Name	Type	description	Minimum	Maximum	Protein Effect	Amino Acid Change	
[0]     [1]     [2]     [3]         [4]     [5]     [6]             [7]                   
CDS Position	Length	# Intervals	Direction	Change	Variant Frequency
[8]             [9]     [10]        [11]        [12]    [13]
Variant P-Value (approximate)	Strand-Bias >50% P-value	Codon Change
[14]                            [15]                        [16]
Coverage	Polymorphism Type	Track Name 	protein_id
[17]        [18]                [19]		[20]
CDS only has relevant data in [4,5,9,11] out of [4,5,9,10,11,19]
gene only has relevant data in [0,3,4,5,9,11] out of [0,3,4,5,9,10,11,19]
Polymorphism has relevant data in [4,5,6,7,8,9,12,13,14,15,18]

the table is ordered by annotation start
there are several issues linked to this, one is that CDS and gene margins 
will not overlap but we need info from both so we will couple them using overlaps()

"""
#SET MAIN VARIABLES
uncoupled_CDS = {}
uncoupled_gene = {}
coupled_s = set()
coupled_d = {}
#storing these data about phatr genes:
"""
coupled_d[gene_id] = {"gene_id": "string", "description": "string", "span": "tuple", \
"CDS Length": "float", "Direction": "string", "Changes": "list", "has_polymorphisms": "yes/no", \
"identified as target": "yes/no"}
"""
#storing data about each polymorphism reported:
polymorphisms_d = {}
"""
polymorphisms_d[PMrange] = {"gene_id": "string", "span": "tuple", "Protein Effect": \
"string", "Amino Acid Change": "string", "CDS Position": "float", "Length": "float", \
"Variant Frequency": "string", "Variant P-Value": "float", "Strand-Bias": "float", \
"Polymorphism Type": "string"}
"""

#ANALYZE INPUT TABLE
current_CDS = {}
current_CDS["X"] = {}
current_gene = {}
current_gene["X"] = {}
trunc_CDS = set()
for r in data:
	row = r.split("\t")
	#get annotation type and process info:
	if len(row) > 1:
		annot_type = row[2]
		annot_min = int(row[4].replace("<",""))
		annot_max = int(row[5].replace(">",""))
		annot_len = float(row[9].replace(">",""))
		if annot_type == "CDS":
			current_CDS["X"] = {
			"tempname": "{}-{}".format(annot_min, annot_max), 
			"span": (annot_min, annot_max), 
			"Length": annot_len, 
			"protein_id": row[20].split(".")[0].replace("draftJ","Jdraft"), 
			"Direction": row[11]}
		elif annot_type == "gene":
			current_gene["X"] = {
			"tempname": "{}-{}".format(annot_min, annot_max), 
			"span": (annot_min, annot_max), 
			"Length": annot_len, 
			"Direction": row[11], 
			"gene_id": row[0], 
			"description": row[3]}
		elif annot_type == "Polymorphism":
			if row[20] != "":
				gene_id = row[20].split(".")[0]
			else:
				gene_id = ""
			if annot_min == annot_max:
				PMrange = str(annot_min)
			else:
				PMrange = "{}-{}".format(annot_min, annot_max)
			#most polymorphisms are not found within CDS:
			try:
				CDSposition = float(row[8])
			except ValueError:
				CDSposition = 0

			#we make a dictionary of all PMs info that can be called by their location
			if PMrange in polymorphisms_d:
				if polymorphisms_d[PMrange]["gene_id"] == "":
					polymorphisms_d[PMrange] = {
					"gene_id": gene_id,
					"range": (annot_min, annot_max),
					"Protein Effect": row[6], 
					"Amino Acid Change": row[7],
					"CDS Position": CDSposition, 
					"Length": annot_len, 
					"Variant Frequency": float(row[13].split("%")[0]), 
					"Variant P-Value": float(row[14]), 
					"Strand-Bias": float(row[15]),
					"Polymorphism Type": row[18]}
			else:
					polymorphisms_d[PMrange] = {
					"gene_id": gene_id, 
					"range": (annot_min, annot_max),
					"Protein Effect": row[6], 
					"Amino Acid Change": row[7],
					"CDS Position": CDSposition, 
					"Length": annot_len, 
					"Variant Frequency": float(row[13].split("%")[0]), 
					"Variant P-Value": float(row[14]), 
					"Strand-Bias": float(row[15]),
					"Polymorphism Type": row[18]}

		elif annot_type == "Type":
			pass #this is the header line, but this has been removed from data earlier
		else:
			print("UNRECOGNIZED ANNOTATION TYPE!")
			reporterrors = True
			errorfile.write("UNRECOGNIZED ANNOTATION TYPE! {}".format(annot_type))


		#decide if CDS and gene annotations overlap, and merge them
		#get is to prevent KeyError with the first line of data
		if current_CDS["X"].get("protein_id", "none") == current_gene["X"].get("gene_id", "any"): 
			gene_id = current_gene["X"]["gene_id"]
			coupled_s.add(gene_id)
			#look if found previously -- in targets_d
			target = targets_d.get(gene_id, "no")

			#check if CDS is very short
			if current_CDS["X"]["Length"] / current_gene["X"]["Length"] < 0.5:
				if len(trunc_CDS) == 0:
					print("Coupled CDS and gene annotations differ a lot in length!".format(gene_id))
				errorfile.write("Coupled CDS/gene differ a lot in length! {}\n".format(gene_id))
				trunc_CDS.add(gene_id)
				reporterrors = True

			#create coupled_d dictionary with merged data about the gene and CDS
			coupled_d[gene_id] = {
			"description": current_gene["X"]["description"], 
			"span": current_CDS["X"]["span"], 
			"CDS Length": current_CDS["X"]["Length"], 
			"Direction": current_CDS["X"]["Direction"], 
			"identified as target": target}

			#remove items that are not uncoupled
			if current_gene["X"]["tempname"] in uncoupled_gene:
				del uncoupled_gene[current_gene["X"]["tempname"]]
			if current_CDS["X"]["tempname"] in uncoupled_CDS:
				del uncoupled_CDS[current_CDS["X"]["tempname"]]
		#if no overlap is present, current annotations are saved in uncoupled dictionaries
		else:
			if annot_type == "gene":
				uncoupled_gene[current_gene["X"]["tempname"]] = current_gene["X"]
				#print("uncoupled genes: {}".format(len(uncoupled_gene.keys())))
			elif annot_type == "CDS":
				uncoupled_CDS[current_CDS["X"]["tempname"]] = current_CDS["X"]
				#print("uncoupled CDSs: {}".format(len(uncoupled_CDS.keys())))

#if there are any apparently truncated CDS models, they get printed here:
if len(trunc_CDS) > 0:
	print("Large difference in CDS length found for: {}".format(", ".join(trunc_CDS)))

#if there are any uncoupled annotations left, try again to pair them:
if len(uncoupled_CDS) > 0 or len(uncoupled_gene) > 0:
	reporterrors = True
	errorfile.write("{} uncoupled CDS, {} uncoupled genes remained\n".format(len(uncoupled_CDS), len(uncoupled_gene)))
	print("{} uncoupled CDS, {} uncoupled genes remained".format(len(uncoupled_CDS), len(uncoupled_gene)))
	matched_CDS = set()
	matched_gene = set()
	for i in uncoupled_CDS:
		span_CDS = (i.split("-")[0], i.split("-")[1])
		cds_id = uncoupled_CDS[i]["protein_id"]
		for j in uncoupled_gene:
			span_gene = (j.split("-")[0], j.split("-")[1])
			gene_id = uncoupled_gene[j]["gene_id"]
			target = targets_d.get(j, "new")
			if cds_id == gene_id:
				coupled_s.add(gene_id)
				coupled_d[gene_id] = {
				"description": uncoupled_gene[j]["description"], 
				"span": uncoupled_gene[j]["span"], 
				"CDS Length": uncoupled_CDS[i]["Length"], 
				"Direction": uncoupled_CDS[i]["Direction"], 
				"identified as target": target}
				matched_CDS.add(i)
				matched_gene.add(j)				
			elif cds_id in gene_id.split("; "):
				#print(uncoupled_CDS[i]["protein_id"],uncoupled_gene[j]["gene_id"])
				coupled_s.add(gene_id)
				coupled_d[gene_id] = {
				"description": uncoupled_gene[j]["description"], 
				"span": uncoupled_gene[j]["span"], 
				"CDS Length": uncoupled_CDS[i]["Length"], 
				"Direction": uncoupled_CDS[i]["Direction"],
				"identified as target": target}
				matched_CDS.add(i)
				matched_gene.add(j)
			# some CDS ranges are wrong: need to determine which ones
			# elif overlaps(span_CDS, span_gene) in ("embed", "overlap"):
			# 	print(uncoupled_CDS[i]["protein_id"],uncoupled_gene[j]["gene_id"])
			# 	target = targets_d.get(j, "new")
			# 	coupled_d[gene_id] = {
			# 	"description": uncoupled_gene[j]["description"], 
			# 	"span": uncoupled_CDS[i]["span"], 
			# 	"CDS Length": uncoupled_CDS[i]["Length"], 
			# 	"Direction": uncoupled_CDS[i]["Direction"],
			# 	"identified as target": target}
			# 	matched_CDS.add(i)
			# 	matched_gene.add(j)	
	for j in matched_gene:
		del uncoupled_gene[j] #26681924-26682837
	for i in matched_CDS:
		del uncoupled_CDS[i]
errorfile.write("After reiteration, {} uncoupled CDS, {} uncoupled gene(s) remained\n"
	.format(len(uncoupled_CDS), len(uncoupled_gene)))
errorfile.write("{}\n".format(", ".join(list(uncoupled_CDS.keys()) + list(uncoupled_gene.keys()))))
print("After reiteration, {} uncoupled CDS, {} uncoupled genes remained".format(len(uncoupled_CDS), len(uncoupled_gene)))


# here we reiterate through PMs and genes to match them
#to assign a list of polymorphisms to genes:
polymorphisms_in_genes = {}
SNPs_in = set()
polymorphisms_near_genes = {}
SNPs_near = set()
#polymorphisms_in_genes[gene_id] = {set()}
uncoupled_id = {}
# maybe a little renaming of subkeys would be appropriate:
for gene in uncoupled_CDS.keys():
	gene_id = uncoupled_CDS[gene]["protein_id"]
	uncoupled_id[gene_id] = uncoupled_CDS[gene]
	uncoupled_id[gene_id].update({"description": "", "identified as target": targets_d.get(gene_id, "no")})
for gene in uncoupled_gene.keys():
	gene_id = uncoupled_gene[gene]["gene_id"]
	uncoupled_id[gene_id] = uncoupled_gene[gene]
	uncoupled_id[gene_id].update({"identified as target": targets_d.get(gene_id, "no")})

print("Assigning SNPs to genes...")
c = 0
print("SNP assignment start time:", time.ctime())
totalPM = len(polymorphisms_d)
uncoupled_CDS_set = set(uncoupled_CDS.keys())
uncoupled_gene_set = set(uncoupled_gene.keys())
all_genes = coupled_s | uncoupled_CDS_set | uncoupled_gene_set
for PMrange in polymorphisms_d:
	c += 1
	if c % 1000 == 0:
		print("progress {}/{}".format(c, totalPM))

	span = polymorphisms_d[PMrange]["range"]
	for gene in all_genes:
		if gene in coupled_s:
			gene_span = coupled_d[gene]["span"]
			gene_id = gene
		elif gene in uncoupled_CDS_set:
			gene_span = uncoupled_CDS[gene]["span"]
			gene_id = uncoupled_CDS[gene]["protein_id"]
		elif gene in uncoupled_gene_set:
			gene_span = uncoupled_gene[gene]["span"]
			gene_id = uncoupled_gene[gene]["gene_id"]
		else:
			gene_span = (0,0)
			gene_id = " "
			print("Error, gene not assigned! {}".format(gene))

		#here we extract PMs within identified genes - this should be after all genes/PMs were loaded!
		if overlaps(span, gene_span) in ("embed", "overlap"):
			SNPs_in.add(span)
			if gene_id not in polymorphisms_in_genes.keys():
				polymorphisms_in_genes[gene_id] = set([PMrange])
			else:		
				polymorphisms_in_genes[gene_id].add(PMrange)
			if gene_id in coupled_d:
				coupled_d[gene_id].update({"has_polymorphisms": polymorphisms_in_genes[gene_id]})
		#optionally, we could extract PMs in close vicinity to genes, say 500bp each direction
		elif overlaps(span, (gene_span[0]-500, gene_span[1]+500)) in ("embed", "overlap"):
			SNPs_near.add(span)
			if gene_id not in polymorphisms_near_genes.keys():
				polymorphisms_near_genes[gene_id] = set([PMrange])
			else:		
				polymorphisms_near_genes[gene_id].add(PMrange)
print("SNP assignment finish time:", time.ctime())
with open("compared_annotations_stats.txt", "w") as stat:
	stat.write("{} SNPs in genes, {} SNPs near genes (+- 500 bp flanking sequence)\n".format(len(SNPs_in), len(SNPs_near - SNPs_in)))
	print("{} SNPs in genes, {} SNPs near genes (+- 500 bp flanking sequence)".format(len(SNPs_in), len(SNPs_near - SNPs_in)))

# filtering and writing results
print("Now to filter and write results...")
notable_mutations = set()
with open("compared_annotations_chosen_targets.txt", "w") as result, \
	open("compared_annotations_details.txt", "w") as details:
	#first we analyze all the polymorphisms and pick the best ones
	#i.e. those that have effect on protein sequence and are frequently recovered
	all_with_polymorphisms = set(polymorphisms_in_genes) | set(polymorphisms_near_genes)
	print("Filtering...")
	for key in all_with_polymorphisms:
		#go through individual polymorphisms and find if:
		if key in polymorphisms_in_genes:
			C = "C"
			# find if PMs are synonymous/nonsynonymous/absent from CDS
			outside = [x for x in polymorphisms_in_genes[key] if polymorphisms_d[x]["Protein Effect"] == ""]
			synonymous = [x for x in polymorphisms_in_genes[key] if polymorphisms_d[x]["Protein Effect"] == "None"]
			deletion = [x for x in polymorphisms_in_genes[key] if polymorphisms_d[x]["Protein Effect"] == "Deletion"]
			nonsynonymous = [x for x in polymorphisms_in_genes[key] if polymorphisms_d[x]["Protein Effect"] == "Substitution"]
			frameshift = [x for x in polymorphisms_in_genes[key] if polymorphisms_d[x]["Protein Effect"] == "Frame Shift"]
			truncation = [x for x in polymorphisms_in_genes[key] if polymorphisms_d[x]["Protein Effect"] in ("Truncation", "Start Codon Loss")]
			extension = [x for x in polymorphisms_in_genes[key] if polymorphisms_d[x]["Protein Effect"] in ("Extension", "Insertion")]
			# are there other types??
			"""for x in polymorphisms_in_genes[key]:
				if x not in (outside + deletion + synonymous + nonsynonymous + frameshift + truncation + extension):
					print("type: {} > {}".format(x, polymorphisms_d[x]["Protein Effect"]))"""
			notable = deletion + nonsynonymous + frameshift + truncation + extension
			notable = [x for x in notable if polymorphisms_d[x]["Variant Frequency"] > 40]
			if len(notable) > 0:
				notable_mutations.add(key)
				N = "N"
			else:
				N = "-"
		else:
			C = "-"
		if key in polymorphisms_near_genes:
			P = "P"
			# check if PMs have high frequency - likelihood of both alleles modified
			notable = [x for x in polymorphisms_near_genes[key] if polymorphisms_d[x]["Variant Frequency"] > 40]
			if len(notable) > 0:
				notable_mutations.add(key)
				N = "N"
			else:
				N = "-"
		else:
			P = "-"
		if key in targets_d:
			T = "T"
		else:
			T = "-"

		#having found the characteristics, now prepare tags and add to coupled_d
		tag = "{}{}{}{}".format(P,C,N,T)
		if key in coupled_d:
			coupled_d[key].update({"polytag": tag})
		elif key in uncoupled_id:
			# this is to avoid key errors later
			coupled_d[key] = uncoupled_id[key]
			length = uncoupled_id[key]["Length"]
			coupled_d[key].update({"polytag": tag, "CDS Length": length})


	#now writing the reports
	print("Writing report files...")
	for key in sorted(notable_mutations):
		details.write("{} {}={}\n".format(key, coupled_d[key]["polytag"], coupled_d[key]["description"]))
		result.write("{}\t{}@{}\ttarget:{}\tpolymorphisms: {}, {}\n".format(key, coupled_d[key]["polytag"], 
		coupled_d[key]["span"], coupled_d[key]["identified as target"], 
		", ".join(sorted(polymorphisms_in_genes.get(key, ["none in transcript"]))), 
		", ".join(sorted(polymorphisms_near_genes.get(key, ["none in flanking"])))))
		if key in polymorphisms_in_genes:
			for p in polymorphisms_in_genes[key]:
				formulation = "{}:{}({}@{:.1f}% length);Freq:{},Pval:{},Strand-Bias:{}".format(p, 
				polymorphisms_d[p]["Protein Effect"], 
				polymorphisms_d[p]["Amino Acid Change"],
				polymorphisms_d[p]["CDS Position"]/coupled_d[key]["CDS Length"]*100,
				polymorphisms_d[p]["Variant Frequency"],
				polymorphisms_d[p]["Variant P-Value"],
				polymorphisms_d[p]["Strand-Bias"])
				details.write("\t{}\n".format(formulation.replace("@0.0% length","flanking")))
		if key in polymorphisms_near_genes:
			for p in polymorphisms_near_genes[key]:
				formulation = "{}:(flanking);Freq:{},Pval:{},Strand-Bias:{}".format(p, 
				polymorphisms_d[p]["Variant Frequency"],
				polymorphisms_d[p]["Variant P-Value"],
				polymorphisms_d[p]["Strand-Bias"])
				details.write("\t{}\n".format(formulation))

fastadb = {}
print("Writing protein fasta for gene functional annotation...")
with open("compared_annotations.fasta", "w") as out:
	for f in fastafile:
		if f.name.split(".")[0] in notable_mutations:
			out.write(">{}\n{}\n".format(f.name, translation(f.seq)))
		elif f.name.split(".")[0] in targets_d:
			out.write(">{}\n{}\n".format(f.name, translation(f.seq)))
	for f in fastafile2:
		if f.name.split(".")[0] in trunc_CDS:
			out.write('>{}_cds_1\n{}\n'.format(f.name, translation(f.seq)))
			out.write('>{}_cds_2\n{}\n'.format(f.name, translation(f.seq[1:])))
			out.write('>{}_cds_3\n{}\n'.format(f.name, translation(f.seq[2:])))
			out.write('>{}_cds_4\n{}\n'.format(f.name, translation(f.seq.reverse_complement())))
			out.write('>{}_cds_5\n{}\n'.format(f.name, translation(f.seq.reverse_complement()[1:])))
			out.write('>{}_cds_6\n{}\n'.format(f.name, translation(f.seq.reverse_complement()[2:])))
			#out.write(">{}_cds\n{}\n".format(f.name, f.seq))
#this file can be further analyzed by InterProScan to retrieve more updated annotations
print("Analysis done.")

if reporterrors:
	decoration = decor("Errors occurred, please refer to: {}".format(errorname))
	decoration()