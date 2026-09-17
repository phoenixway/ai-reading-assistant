from app.protocol import parse_output

def test_multispan_and_contract():
    raw='''SUM: Things happen.\nWHO: mara,levin\nEV: Mara opens the envelope @03-04\nSAY: mara | only an invoice @05\nEND: present=mara,levin | loc=kitchen | situation=they are silent @P05'''
    p=parse_output(raw,set(range(1,10)))
    assert p.contract_pass
    assert p.records[2].spans == [3,4]
