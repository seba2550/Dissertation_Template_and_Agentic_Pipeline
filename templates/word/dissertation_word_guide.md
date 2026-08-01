# Microsoft Word Dissertation Specification & Style Guide (UCSF & ProQuest Compliant)

This specification outlines the exact styles, page setups, fields, and formatting rules required to make Microsoft Word (`.docx`) dissertations 100% compliant with institutional guidelines (UCSF Graduate Division & ProQuest).

---

## 1. Document & Page Layout Setup

| Parameter | Value / Requirement | Implementation in MS Word |
| :--- | :--- | :--- |
| **Paper Size** | Letter (8.5" x 11") | Layout -> Size -> Letter |
| **Margins** | 1.0 inch (2.54 cm) on all 4 sides | Layout -> Margins -> Custom Margins (Top: 1", Bottom: 1", Left: 1", Right: 1") |
| **Gutter** | 0 inches | Set Gutter to 0" (ProQuest electronic PDF submission) |
| **Line Spacing** | Double Spaced (Body Text) | Paragraph -> Line Spacing -> Double (0 pt space before/after) |
| **Primary Font** | Times New Roman (12 pt) or Georgia (11-12 pt) or Arial (10-12 pt) | Modify `Normal` style |
| **Text Color** | Pure Black (`#000000`) | Set Font Color to Automatic / Black |

---

## 2. Style Hierarchy & Formatting Rules

### Custom Style Specifications

Modify Word's built-in styles to enforce consistency throughout the document:

1. **`Normal` Style (Body Text)**
   - **Font**: Times New Roman, 12 pt, Regular, Black.
   - **Paragraph**: Alignment Left (or Justified), First line indent `0.5 in`, Line Spacing `Double`, Space Before `0 pt`, Space After `0 pt`.

2. **`Heading 1` (Chapter Titles)**
   - **Font**: Times New Roman, 14-16 pt, Bold, Black.
   - **Paragraph**: Centered, Line Spacing `Double` or `Single`, Space Before `24 pt`, Space After `18 pt`.
   - **Break**: Check `Page break before` in Paragraph -> Line and Page Breaks.

3. **`Heading 2` (Main Sections)**
   - **Font**: Times New Roman, 13-14 pt, Bold, Black.
   - **Paragraph**: Left-aligned, Line Spacing `Double`, Space Before `12 pt`, Space After `6 pt`.

4. **`Heading 3` (Subsections)**
   - **Font**: Times New Roman, 12 pt, Bold/Italic, Black.
   - **Paragraph**: Left-aligned, Line Spacing `Double`, Space Before `6 pt`, Space After `2 pt`.

5. **`Caption` (Figures & Tables)**
   - **Font**: Times New Roman, 10-11 pt, Regular/Bold lead-in, Black.
   - **Spacing**: Single Spaced.
   - **Placement**:
     - **Table Captions**: ABOVE the table.
     - **Figure Captions**: BELOW the figure.

6. **`Block Text` (Long Quotations > 4 lines)**
   - **Font**: Times New Roman, 11-12 pt, Regular.
   - **Paragraph**: Single Spaced, Left Indent `0.5 in`, Right Indent `0.5 in`, Space Before `6 pt`, Space After `6 pt`.

---

## 3. Section Breaks & Page Numbering Architecture

UCSF and ProQuest require two distinct page numbering schemes in a single document:

```
[ Title Page ] -------------> Counted as Page i (NO printed page number)
[ Copyright, Abstract, etc.] -> Lowercase Roman numerals (ii, iii, iv...)
============================= [ SECTION BREAK (NEXT PAGE) ]
[ Chapter 1 to End ] -------> Arabic numerals starting at Page 1 (1, 2, 3...)
```

### Step-by-Step Implementation:
1. **Title Page**: Do NOT insert a page number on Page 1.
2. **Insert Section Break**: At the bottom of the Title Page, select `Layout -> Breaks -> Section Breaks -> Next Page`.
3. **Unlink Headers/Footers**: Click in the Footer of Section 2. Uncheck `Link to Previous`.
4. **Roman Numerals**: Insert Page Number -> Bottom of Page (Center or Right, at least 0.5 inches from bottom edge). Format Page Numbers -> Number Format: `i, ii, iii...`, Start at: `ii`.
5. **Arabic Numerals**: Before Chapter 1, insert another `Section Break (Next Page)`. Click in Footer of Section 3, uncheck `Link to Previous`. Insert Page Number -> Format Page Numbers -> `1, 2, 3...`, Start at: `1`.

---

## 4. Tables, Figures & Captions

- **Table Formatting**: Use simple, professional borders (top border, header line, bottom line - equivalent to LaTeX `booktabs`). Do not use heavy gridlines or vibrant background colors.
- **Figure Resolution**: Ensure graphics embedded in Word are vector PDF/EMF or high-resolution PNG/TIFF (>= 300 DPI).
- **Automated Caption Fields**: Use Word's `References -> Insert Caption` feature so that figures and tables auto-number and populate the Table of Figures automatically.

---

## 5. Reference Manager Integration

For Word-based workflows, use a citation manager (e.g. EndNote, Zotero, or Mendeley) configured with:
- **Style**: Standard Numeric (Vancouver or AMA) or Author-Year (APA 7th).
- **DOI Inclusion**: Mandatory for digital references.
- **Final Export**: Prior to submission, generate a unfielded/clean copy (`Convert to Plain Text`) to ensure field codes don't corrupt during PDF conversion.
