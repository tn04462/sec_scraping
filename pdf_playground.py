pdf = r"C:\Users\Olivi\OneDrive\QuickShare\13flist2022q1.pdf"


from tabula import read_pdf
from pathlib import Path
 
#reads table from pdf file
import pandas as pd

def convert_13f_securities_pdf(pdf_path: str, target_path: str=None, mode: str="csv", overwrite=True)
    '''
    Args:
        pdf_path: path to the pdf file
        target_path: output file
        mode: set output mode. valid modes are: 'csv'
    
    Raises:
        ValueError: if mode requires target_path but it is None
        FileExistsError: if overwrite is False and a file already exists at target_path
    '''
    df = read_pdf(pdf,pages="all", pandas_options={"header": None})
    # print(pd.DataFrame(df))
    if mode == "csv":
        if target_path is None:
            raise ValueError("must set target_path if mode='csv'")
        if Path(target_path).is_file():
            if overwrite is False:
                raise FileExistsError("a file with that name already exists")
            else:
                Path(target_path).unlink()
    for d in df:
        if d.shape[1] == 5:
            d = d.drop(d.columns[1], axis="columns")
        if d.shape[1] == 4:
            d = d.drop(d.columns[-1], axis="columns")
        if mode == "csv":
            d.to_csv(target_path, mode="a", index=False, header=False)
