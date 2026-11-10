"""
Hospitality Operations Dashboard - data preparation
1. Cleans the raw hotel bookings data.
2. Saves a clean booking-level file for Power BI / Tableau (outputs/hotel_bookings_clean.csv).
3. Saves a summary table and prints the headline numbers.
4. Builds the interactive dashboard (dashboard/index.html) by embedding an
   aggregated data cube into src/dashboard_template.html.

Run from the project folder:  python src/prepare_data.py
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "hotel_bookings.csv"
CLEAN = ROOT / "outputs" / "hotel_bookings_clean.csv"
SUMMARY = ROOT / "outputs" / "summary_by_hotel_channel.csv"
TEMPLATE = ROOT / "src" / "dashboard_template.html"
DASHBOARD = ROOT / "dashboard" / "index.html"

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]
SEASON = {12: "Winter", 1: "Winter", 2: "Winter", 3: "Spring", 4: "Spring", 5: "Spring",
          6: "Summer", 7: "Summer", 8: "Summer", 9: "Fall", 10: "Fall", 11: "Fall"}
CHANNEL = {"Online TA": "Online travel agent", "Offline TA/TO": "Offline travel agent",
           "Groups": "Groups", "Direct": "Direct", "Corporate": "Corporate"}


LEAD_BANDS = ["0-7 days", "8-30 days", "31-90 days", "91-180 days", "181-365 days", "365+ days"]


def lead_band(days: int) -> str:
    if days <= 7:
        return "0-7 days"
    if days <= 30:
        return "8-30 days"
    if days <= 90:
        return "31-90 days"
    if days <= 180:
        return "91-180 days"
    if days <= 365:
        return "181-365 days"
    return "365+ days"


def clean(df: pd.DataFrame) -> pd.DataFrame:
    start = len(df)
    df["nights"] = df["stays_in_weekend_nights"] + df["stays_in_week_nights"]
    df["guests"] = df["adults"] + df["children"].fillna(0) + df["babies"]
    checks = {
        "zero-night stays": df["nights"] == 0,
        "bookings with zero guests": df["guests"] == 0,
        "negative or extreme ADR (<0 or >1000)": (df["adr"] < 0) | (df["adr"] > 1000),
    }
    remove = pd.Series(False, index=df.index)
    for label, mask in checks.items():
        print(f"  {label}: {int((mask & ~remove).sum())}")
        remove |= mask
    df = df[~remove].copy()
    print(f"  rows kept: {len(df):,} of {start:,}")

    df["month_num"] = df["arrival_date_month"].map({m: i + 1 for i, m in enumerate(MONTHS)})
    df["year_month"] = df["arrival_date_year"].astype(str) + "-" + df["month_num"].astype(str).str.zfill(2)
    df["season"] = df["month_num"].map(SEASON)
    df["channel"] = df["market_segment"].map(CHANNEL).fillna("Other")
    df["lead_band"] = df["lead_time"].apply(lead_band)
    df["lead_band_order"] = df["lead_band"].map({b: i + 1 for i, b in enumerate(LEAD_BANDS)})
    df["booking_revenue"] = (df["adr"] * df["nights"]).round(2)
    df["realized_revenue"] = df["booking_revenue"].where(df["is_canceled"] == 0, 0)
    df["lost_revenue"] = df["booking_revenue"].where(df["is_canceled"] == 1, 0)
    return df


def build_cube(df: pd.DataFrame) -> list:
    """Aggregate to hotel x month x channel x lead band, small enough to embed in HTML."""
    df = df.assign(stayed_nights=df["nights"].where(df["is_canceled"] == 0, 0))
    g = df.groupby(["hotel", "year_month", "season", "channel", "lead_band"], observed=True)
    cube = g.agg(
        bookings=("is_canceled", "size"),
        canceled=("is_canceled", "sum"),
        lead_sum=("lead_time", "sum"),
        nights=("stayed_nights", "sum"),
        revenue=("realized_revenue", "sum"),
        lost=("lost_revenue", "sum"),
    ).reset_index()
    cube["revenue"] = cube["revenue"].round(0)
    cube["lost"] = cube["lost"].round(0)
    # short keys keep the embedded file small
    cube.columns = ["h", "ym", "s", "c", "l", "b", "x", "lt", "n", "r", "lo"]
    return cube.to_dict(orient="records")


def headline(df: pd.DataFrame):
    stayed = df[df["is_canceled"] == 0]
    print("\nHeadline numbers")
    print(f"  bookings: {len(df):,}")
    print(f"  cancellation rate: {df['is_canceled'].mean():.1%}")
    print(f"  average lead time: {df['lead_time'].mean():.0f} days")
    print(f"  ADR (stayed bookings): ${stayed['booking_revenue'].sum() / stayed['nights'].sum():.2f}")
    print(f"  realized revenue: ${df['realized_revenue'].sum():,.0f}")
    print(f"  revenue lost to cancellations: ${df['lost_revenue'].sum():,.0f} "
          f"({df['lost_revenue'].sum() / df['booking_revenue'].sum():.1%} of booked revenue)")
    for col in ["hotel", "channel", "lead_band", "season", "deposit_type"]:
        t = df.groupby(col).agg(bookings=("is_canceled", "size"),
                                cancel_rate=("is_canceled", "mean"),
                                lost=("lost_revenue", "sum")).sort_values("cancel_rate", ascending=False)
        t["cancel_rate"] = (t["cancel_rate"] * 100).round(1)
        t["lost"] = t["lost"].round(0)
        print(f"\nBy {col}\n{t.to_string()}")


def main():
    print("Cleaning")
    df = clean(pd.read_csv(RAW))

    CLEAN.parent.mkdir(parents=True, exist_ok=True)
    keep = ["hotel", "is_canceled", "lead_time", "lead_band", "lead_band_order", "arrival_date_year", "arrival_date_month",
            "month_num", "year_month", "season", "nights", "guests", "channel", "market_segment",
            "distribution_channel", "deposit_type", "customer_type", "is_repeated_guest", "adr",
            "booking_revenue", "realized_revenue", "lost_revenue", "country"]
    df[keep].to_csv(CLEAN, index=False)

    summary = df.groupby(["hotel", "channel"]).agg(
        bookings=("is_canceled", "size"),
        cancellation_rate=("is_canceled", "mean"),
        avg_lead_time=("lead_time", "mean"),
        realized_revenue=("realized_revenue", "sum"),
        lost_revenue=("lost_revenue", "sum"),
    ).round(3).reset_index()
    summary.to_csv(SUMMARY, index=False)

    headline(df)

    cube = build_cube(df)
    html = TEMPLATE.read_text().replace("/*__DATA__*/[]", json.dumps(cube, separators=(",", ":")))
    DASHBOARD.parent.mkdir(parents=True, exist_ok=True)
    DASHBOARD.write_text(html)
    print(f"\nSaved {CLEAN.name}, {SUMMARY.name} and dashboard/index.html ({len(cube):,} cube rows)")


if __name__ == "__main__":
    main()
