import csv

def to_float(val):
    """Try converting a string to float; return None if conversion fails."""
    try:
        return float(val)
    except (ValueError, TypeError):
        return None

def get_val(row, post_key, pre_key):
    """
    Returns the float value from row[post_key] if available; otherwise, from row[pre_key].
    """
    val = to_float(row.get(post_key, ""))
    if val is None:
        val = to_float(row.get(pre_key, ""))
    return val

def interpret_pft(csv_path):
    """
    Reads the CSV file with table data and returns a multiline string interpretation of the PFT results.
    
    Expected CSV structure:
      - Header row: ["var", "pre", "zscore", "lln", "%predpre", "post", "zscore post", "%predpost", "%changepost"]
      - The first column of each subsequent row is the row title.
    
    Interpretation Guidelines:
      • SPIROMETRY:
          - Obstruction is defined as FEV1/FVC (post if available, else pre) < LLN and its z‐score (post or pre) < –1.645.
          - Severity (based on FEV1 z‐score; post if available, else pre):
                if zscore ≥ –1.645: (not abnormal; should not reach this branch)
                if –2.5 ≤ zscore < –1.645: mild
                if –4.0 ≤ zscore < –2.5: moderate
                if zscore < –4.0: severe
      • Bronchodilator response is reported only if post values exist.
      • LUNG VOLUMES:
          - Restriction is determined using TLC (post if available, else pre) < LLN and TLC z‐score < –1.645,
            with severity based on FVC z‐score (using the same thresholds as above).
          - Hyperinflation is flagged if TLC z‐score > +1.65.
          - Air trapping is described as: “Evidence of air trapping is present” if either RV/TLC z‐score (post or pre) > +1.65 or RV %pred (post if available, else pre) > 175.
      • DLCO:
          - Low DLCO is defined as DLCO z‐score < –1.645 with severity graded using the same thresholds.
      • Test Grade:
          - If test grade (from row "testgrade") is not "AA", it is noted.
    
    Returns a multiline string with section headers.
    """
    # Parse CSV into a mapping: row_title -> {column_title: value}
    data = {}
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)
    if not rows or len(rows) < 2:
        return "No data available."
    header = rows[0]
    for row in rows[1:]:
        row_title = row[0].strip()
        data[row_title] = dict(zip(header[1:], row[1:]))
    
    # Convenience mapping for key rows.
    fvc = data.get("fvc", {})
    fev1 = data.get("fev1", {})
    fev1_fvc = data.get("fev1/fvc", {})
    testgrade = data.get("testgrade", {})
    tlc = data.get("tlcpleth", {})
    rv = data.get("rvpleth", {})
    rv_tlc = data.get("rv/tlcpleth", {})
    dlco = data.get("dlcocor", {})
    dlcounc = data.get("dlcounc", {})
    
    ### SPIROMETRY ###
    # Use FEV1/FVC value (post if available, else pre).
    fev1fvc_value = get_val(fev1_fvc, "post", "pre")
    fev1fvc_lln = to_float(fev1_fvc.get("lln", ""))
    fev1fvc_z = get_val(fev1_fvc, "zscore post", "zscore")
    obstruction = False
    if fev1fvc_value is not None and fev1fvc_lln is not None and fev1fvc_z is not None:
        if (fev1fvc_value < fev1fvc_lln) and (fev1fvc_z < -1.645):
            obstruction = True

    # Determine severity using FEV1 z‐score.
    fev1_z = get_val(fev1, "zscore post", "zscore")
    if fev1_z is not None:
        if fev1_z >= -1.645:
            obstr_severity = ""
        elif fev1_z >= -2.5:
            obstr_severity = "mild"
        elif fev1_z >= -4.0:
            obstr_severity = "moderate"
        else:
            obstr_severity = "severe"
    else:
        obstr_severity = ""
    
    # Check for a restrictive pattern from spirometry using FVC.
    fvc_post_val = get_val(fvc, "post", "pre")
    fvc_lln = to_float(fvc.get("lln", ""))
    fvc_z = get_val(fvc, "zscore post", "zscore")
    possible_restriction = False
    if fvc_post_val is not None and fvc_lln is not None and fvc_z is not None:
        if fvc_post_val < fvc_lln and fvc_z < -1.645:
            possible_restriction = True
    # Determine restriction severity using FVC z‐score.
    if fvc_z is not None:
        if fvc_z >= -1.645:
            restr_severity = ""
        elif fvc_z >= -2.5:
            restr_severity = "mild"
        elif fvc_z >= -4.0:
            restr_severity = "moderate"
        else:
            restr_severity = "severe"
    else:
        restr_severity = ""
    
    # Build spirometry section.
    if obstruction and possible_restriction:
        spirometry_section = (f"Spirometry:\nMixed obstructive/restrictive lung function impairment "
                              f"(Obstructive severity: {obstr_severity}; Restrictive severity: {restr_severity}).")
    elif obstruction:
        spirometry_section = f"Spirometry:\nObstructive lung function impairment (severity: {obstr_severity})."
    elif possible_restriction:
        spirometry_section = f"Spirometry:\nRestrictive lung function impairment (severity: {restr_severity})."
    else:
        spirometry_section = "Spirometry:\nNormal postbronchodilator spirometry."
    
    ### BRONCHODILATOR RESPONSE ###
    if fvc.get("post") or fev1.get("post"):
        bo_response = False
        fvc_pre_val = to_float(fvc.get("pre", ""))
        fvc_post_val = to_float(fvc.get("post", ""))
        if fvc_pre_val and fvc_post_val and fvc_pre_val > 0:
            if (fvc_post_val - fvc_pre_val) / fvc_pre_val >= 0.10:
                bo_response = True
        fev1_pre_val = to_float(fev1.get("pre", ""))
        fev1_post_val = to_float(fev1.get("post", ""))
        if fev1_pre_val and fev1_post_val and fev1_pre_val > 0:
            if (fev1_post_val - fev1_pre_val) / fev1_pre_val >= 0.10:
                bo_response = True
        bo_section = "Bronchodilator Response:\nPresent." if bo_response else "Bronchodilator Response:\nNot present."
    else:
        bo_section = ""
    
    ### LUNG VOLUMES ###
    tlc_post_val = get_val(tlc, "post", "pre")
    tlc_lln_val = to_float(tlc.get("lln", ""))
    tlc_z = get_val(tlc, "zscore post", "zscore")
    lung_restriction = False
    if tlc_post_val is not None and tlc_lln_val is not None and tlc_z is not None:
        if tlc_post_val < tlc_lln_val and tlc_z < -1.645:
            lung_restriction = True
    lung_vol_section = "Lung Volumes:\n"
    if lung_restriction:
        lung_vol_section += f"Restrictive lung function impairment (severity: {restr_severity}). "
    if tlc_z is not None and tlc_z > 1.65:
        lung_vol_section += "Hyperinflation is present. "
    rv_tlc_z = get_val(rv_tlc, "zscore post", "zscore")
    rv_pred = get_val(rv, "%predpost", "%predpre")
    if (rv_tlc_z is not None and rv_tlc_z > 1.65) or (rv_pred is not None and rv_pred > 175):
        lung_vol_section += "\nEvidence of air trapping is present."
    if lung_vol_section.strip() == "Lung Volumes:":
        lung_vol_section = "Lung Volumes:\nNormal lung volumes."

    
    ### DLCO ###
    dlco_z = to_float(dlco.get("zscore", ""))
    dlco_unc_z = to_float(dlcounc.get("zscore", ""))
    
    if dlco_z is not None and dlco_z < -1.645:
        if dlco_z >= -2.5:
            dlco_severity = "mild"
        elif dlco_z >= -4.0:
            dlco_severity = "moderate"
        else:
            dlco_severity = "severe"
        dlco_section = f"DLCO:\n{dlco_severity} reduction in DLCO."
    elif dlco_unc_z is not None and dlco_unc_z < -1.645:
        if dlco_unc_z >= -2.5:
            dlco_severity = "mild"
        elif dlco_unc_z >= -4.0:
            dlco_severity = "moderate"
        else:
            dlco_severity = "severe"
        dlco_section = f"DLCO:\n{dlco_severity} reduction in DLCO (uncorrected)."
    else:
        if dlco_unc_z is None or dlco_unc_z >= -1.645:
            dlco_section = "DLCO:\nNormal DLCO."
        else:
            dlco_section = "DLCO:\nNormal DLCO (uncorrected)."
    
    ### TEST GRADE ###
    test_grade_val = testgrade.get("post", "").strip().upper() if testgrade.get("post") else ""
    if test_grade_val and test_grade_val != "AA":
        grade_section = f"Test Grade:\n{test_grade_val}."
    else:
        grade_section = "Test Grade:\nAA."
    
    # Build final interpretation.
    sections = [grade_section, spirometry_section]
    if bo_section:
        sections.append(bo_section)
    sections.extend([lung_vol_section, dlco_section])
    interpretation = "\n\n".join(sections)
    
    return interpretation

if __name__ == "__main__":
    csv_file = "output/table_data.csv"  # Adjust path as needed
    report = interpret_pft(csv_file)
    print("PFT Interpretation Report:")
    print(report)
