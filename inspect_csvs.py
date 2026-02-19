import pandas as pd, glob, os
folder=r'C:\Users\W1 TI\OneDrive - W1\Documentos\Dados'
files=sorted(glob.glob(os.path.join(folder,'*.csv')))
print('Found',len(files),'csv files:')
for f in files:
    print('-',os.path.basename(f))
    try:
        df=pd.read_csv(f,encoding='utf-8',sep=';',nrows=5)
    except Exception as e:
        try:
            df=pd.read_csv(f,encoding='latin-1',sep=',',nrows=5)
        except Exception as e2:
            print('  Could not read head:',e2)
            continue
    print('  cols:',list(df.columns))
    if 'ID' in df.columns:
        ids=df['ID'].dropna().astype(str)
        if not ids.empty:
            print('  first ID sample:', ids.iloc[0])
