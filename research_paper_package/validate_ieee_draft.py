#!/usr/bin/env python3

from pathlib import Path
import re
import pandas as pd


def main() -> None:
    tex_path = Path("research_paper_package/ieee_paper_draft.tex")
    bib_path = Path("research_paper_package/references.bib")

    tex = tex_path.read_text(encoding="utf-8")
    bib = bib_path.read_text(encoding="utf-8")

    cite_blocks = re.findall(r"\\cite\{([^}]*)\}", tex)
    cited = set()
    for block in cite_blocks:
        for key in block.split(","):
            key = key.strip()
            if key:
                cited.add(key)

    bib_keys = set(re.findall(r"@\w+\{([^,]+),", bib))

    missing = sorted(cited - bib_keys)
    unused = sorted(bib_keys - cited)

    print("cited_count=", len(cited))
    print("missing_in_bib=", missing)
    print("unused_in_bib_count=", len(unused))

    # Numeric consistency spot checks from output tables
    b = pd.read_csv("research_paper_package/output_simulation/table_descriptive_binary.csv")
    h0 = pd.read_csv("research_paper_package/output_simulation/table_hypothesis_tests.csv")
    h1 = pd.read_csv("research_paper_package/output_simulation_control_v1/table_hypothesis_tests.csv")

    v0_acc = float(b[(b.variant == "V0") & (b.metric == "intro_accepted")].iloc[0].rate * 100)
    v4_acc = float(b[(b.variant == "V4") & (b.metric == "intro_accepted")].iloc[0].rate * 100)

    row_h2 = h1[(h1.metric == "intro_accepted") & (h1.control == "V1") & (h1.treatment == "V4")].iloc[0]

    checks = {
        "has_1456": "14.56\\%" in tex,
        "has_2274": "22.74\\%" in tex,
        "has_h2_v1_row": "Acceptance rate & V4 vs V1" in tex,
        "acceptance_numbers_rounded_ok": round(v0_acc, 2) == 14.56 and round(v4_acc, 2) == 22.74,
        "h2_row_expected_p": row_h2.p_value,
    }

    for k, v in checks.items():
        print(f"{k}= {v}")


if __name__ == "__main__":
    main()
