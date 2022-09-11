***

## sec_scraping
The aim of this repository is to be able to easily parse SEC-filings and create a model that can be used with a database. Created for dilutionscout.com.

#### Parsers
using parser directly:
```python
from main.parser import parsers

filing_path = r"absolut_path/to/filing.htm"
parser = parsers.Parser8K()
filing_sections = parser.parse(filing_path)
```


using parser through FilingFactory
```python

from main.parser.parsers import Parsers8K, ParserEFFECT, BaseHTMFiling, BaseFiling, FilingFactory, ParserFactory

# register parser for form type and file extension
parser_factory_default = [
    (".htm", "8-K", Parser8K),
    (".xml", "EFFECT", ParserEFFECT)

]
parser_factory = ParserFactory(defaults=parser_factory_default)

# register object which handles parsing
filing_factory_defaults = [
    ("8-K", ".htm", BaseHTMFiling),
    ("EFFECT", ".xml", BaseFiling)
]
filing_factory = FilingFactory(defaults=filing_factory_defaults)

filing_path_8k = r"absolut_path/to/filing_8k.htm"

parsed_filing = filing_factory.create_filing("8-K", ".htm", path=filing_path_8k)

```

#### Extractors
WIP

#### filing_nlp
WIP

#### XBRL Fact search
if you want to extract XBRL facts from sec companyfacts files check the data_aggregation folder
    1. use pysec-downloader package to retrieve companyfacts or run bulk_files.py to retrieve
        companyfacts and submissions files (around 25GB of files)
    2. use the _get_fact_data function from fact_extractor.py to get a specific fact/
        or facts matching a regex pattern


---

## how to setup dilution_db:
0. Fork/clone repository
1. Create an empty database in postgresql
2. make a copy of the public.env file or add it to gitignore
3. Fill the .env file with the database info
4. Add paths for files to the .env
5. Add the polygon API key to the .env. Get a free polygon api key if you havnt got one. [polygon pricing page](https://polygon.io/pricing)
6. specify what companies and what sec forms to track in main/configs.py (class AppConfig)
7. do (in a file above the main directory):

```python
    from dilution_db import DilutionDB
    from main.configs import FactoryConfig, GlobalConfig
    from boot import bootstrap_dilution_db
    
    config = FactoryConfig(GlobalConfig(ENV_STATE="prod").ENV_STATE)()

    db = bootstrap_dilution_db(
        start_orm=True,
        config=config
    )
    db.inital_setup()
    # this will download at least 20GB of bulk data, the base info for the company and all filings of the specified forms, and will try to parse the filings and write to the database 
```
## accessing company data through the model

***


    




