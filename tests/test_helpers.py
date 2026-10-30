"""
Shared test fixtures and helpers for the Dissertation Pipeline test suite.
"""

import os
import zipfile


def create_sample_docx(path: str):
    """
    Creates a minimal, valid OpenXML Word (.docx) document containing:
    - Relationship hyperlinks (DOI, PubMed, BioRxiv)
    - OpenXML Heading styles (Heading1, Heading2, Heading3)
    - Markdown-style headings (# Title, ## Section)
    - Text citations and plain DOIs
    - Block quotations
    """
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""

    rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

    doc_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" Target="https://doi.org/10.1038/nature12345" TargetMode="External"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" Target="https://pubmed.ncbi.nlm.nih.gov/38196633/" TargetMode="External"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" Target="https://www.biorxiv.org/content/10.1101/2023.01.01.123456v1" TargetMode="External"/>
</Relationships>"""

    document = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <w:body>
    <w:p>
      <w:pPr><w:pStyle w:val="Heading1"/></w:pPr>
      <w:r><w:t>Introduction and Background</w:t></w:r>
    </w:p>
    <w:p>
      <w:r><w:t>Epigenetic mechanisms control cellular differentiation and aging. Seminal work by Horvath </w:t></w:r>
      <w:hyperlink r:id="rId1"><w:r><w:t>[1]</w:t></w:r></w:hyperlink>
      <w:r><w:t> demonstrated tissue-independent clocks, while subsequent studies </w:t></w:r>
      <w:hyperlink r:id="rId2"><w:r><w:t>[2]</w:t></w:r></w:hyperlink>
      <w:r><w:t> analyzed multi-ancestry cohorts. Additional findings were reported in 10.1016/j.cell.2020.01.001.</w:t></w:r>
    </w:p>
    <w:p>
      <w:pPr><w:pStyle w:val="Heading2"/></w:pPr>
      <w:r><w:t>Methods and Statistical Procedures</w:t></w:r>
    </w:p>
    <w:p>
      <w:r><w:t>Details of the regression models and imputation procedures applied across cohorts.</w:t></w:r>
    </w:p>
    <w:p>
      <w:pPr><w:pStyle w:val="Quote"/></w:pPr>
      <w:r><w:t>Aging is a multifaceted biological decline driven by molecular and cellular damage accumulating progressively over chronological time throughout organismal lifespan.</w:t></w:r>
    </w:p>
    <w:p>
      <w:r><w:t># Discussion and Future Perspectives</w:t></w:r>
    </w:p>
    <w:p>
      <w:r><w:t>## Population Diversity in Biomarkers</w:t></w:r>
    </w:p>
    <w:p>
      <w:r><w:t>Summary of findings across diverse cohorts and translational implications.</w:t></w:r>
    </w:p>
  </w:body>
</w:document>"""

    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with zipfile.ZipFile(path, 'w') as z:
        z.writestr('[Content_Types].xml', content_types)
        z.writestr('_rels/.rels', rels)
        z.writestr('word/_rels/document.xml.rels', doc_rels)
        z.writestr('word/document.xml', document)
