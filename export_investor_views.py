# export_investor_views.py
import os
from investor_views import load_master, get_investor_view

OUTPUT_FOLDER = "data_curated/investor_views"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def main():
    df_master = load_master()
    print("Master shape:", df_master.shape)

    for key in ["real_estate", "agriculture", "transport", "telecom", "retail", "fintech"]:
        df_view, meta = get_investor_view(df_master, key)
        print(f"\n--- {meta['label']} ({key}) ---")
        print("View shape:", df_view.shape)
        print("Primary:", meta["primary"])
        print("Filters:", meta["filters"])

        # Export CSV for this investor type
        out_path = os.path.join(OUTPUT_FOLDER, f"{key}_view.csv")
        df_view.to_csv(out_path, index=False)
        print(f"Saved {out_path}")

if __name__ == "__main__":
    main()
