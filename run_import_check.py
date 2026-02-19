from dash_board_metricas import load_and_consolidate_all_data
import glob, os

folder=r'C:\Users\W1 TI\OneDrive - W1\Documentos\Dados'
files=sorted(glob.glob(os.path.join(folder,'*.csv')))
consolidated = load_and_consolidate_all_data(files)
print('\nConsolidated projects:', list(consolidated.keys()))
for k,v in consolidated.items():
    print(f" - {k}: {len(v)} rows")

# Quick check for S1NC presence
if 'S1NC' in consolidated:
    print('S1NC detected with', len(consolidated['S1NC']), 'rows')
else:
    print('S1NC not detected in consolidated data')
