from fieldnote.data import rows
from fieldnote.index import Index, Page, answer, parse_date, squash

PAGES = [Page("001", "image", rows([("BOOK TA.K SDN BHD", (10, 10, 200, 30)), ("DATE: 25/12/2018", (10, 40, 200, 60)),
                                    ("TOTAL QTY", (10, 70, 80, 90)), ("3", (150, 70, 160, 90)),
                                    ("TOTAL", (10, 100, 80, 120)), ("9.00", (150, 100, 200, 120)),
                                    ("CASH", (10, 130, 80, 150)), ("20.00", (150, 130, 200, 150))]), "001.jpg"),
         Page("002", "image", [("GARDENIA BAKERIES", (0, 0, 10, 10)), ("2018-03-01", (0, 20, 10, 30)), ("TOTAL RM 4.50", (0, 40, 10, 50))],
              "002.jpg"),
         Page("003", "text", [("Store policy: refunds within 30 days", (0, 0, 0, 0))], "policy.md")]


def test_ocr_spacing_does_not_matter():
    assert squash("BOOKTA_K(TAMANDAYA)SDNBHD") == squash("Book Ta.K (Taman Daya) Sdn Bhd")


def test_retrieval_by_modality_and_fusion():
    idx = Index(PAGES)
    assert idx.search("total on the book ta k sdn bhd receipt", modality="image")[0][0].id == "001"
    assert idx.search("refunds", modality="text")[0][0].id == "003"
    assert idx.fused("gardenia bakeries receipt")[0].id == "002"


def test_answers_come_with_the_row_and_box_they_were_read_from():
    value, row, box = answer(PAGES[0], "total")
    assert value == "9.00" and row == "TOTAL 9.00" and box == (10, 100, 200, 120)     # not the quantity, not the cash
    assert answer(PAGES[0], "date")[0] == "2018-12-25" and answer(PAGES[1], "date")[0] == "2018-03-01"
    assert parse_date("25 DEC 2018") == "2018-12-25"
