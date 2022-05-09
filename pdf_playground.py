pdf = r"C:\Users\Olivi\OneDrive\QuickShare\13flist2022q1.pdf"


from tabula import read_pdf
 
#reads table from pdf file
import pandas as pd
df = read_pdf(pdf,pages="all") #address of pdf file
# print(pd.DataFrame(df))
print(type(df))
print(len(df))
print(df[0])
df[0].to_csv(r"C:\Users\Olivi\OneDrive\QuickShare\13flist2022q1_p3.csv", mode="w", index=False)
for d in df[1:]:
    d.to_csv(r"C:\Users\Olivi\OneDrive\QuickShare\13flist2022q1_p3.csv", mode="a", index=False, header=False)
