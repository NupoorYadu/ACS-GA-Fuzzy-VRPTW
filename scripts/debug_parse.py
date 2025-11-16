from src.io.solomon_loader import parse_solomon
p = parse_solomon('data/solomon/R1/raw/R101.csv')
print('n_lines', p['n_lines'])
print('depot', p['depot'])
print('n_customers', len(p['customers']))
print('first 5 raw_preview:')
for ln in p['raw_preview'][:5]:
    print(repr(ln))
