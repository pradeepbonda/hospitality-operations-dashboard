# Power BI version: DAX measures

To rebuild this dashboard in Power BI Desktop:

1. **Get Data → Text/CSV** and load `outputs/hotel_bookings_clean.csv`. Name the table `Bookings`.
2. In Power Query, check that `adr`, `booking_revenue`, `realized_revenue` and `lost_revenue` are Decimal Number and `lead_time` and `nights` are Whole Number.
3. Create the measures below (**Modeling → New measure**).
4. Add slicers for `hotel`, `season` and `channel`, card visuals for the KPIs, and charts as listed at the end.

## Measures

```DAX
Total Bookings = COUNTROWS ( Bookings )

Canceled Bookings = CALCULATE ( [Total Bookings], Bookings[is_canceled] = 1 )

Cancellation Rate = DIVIDE ( [Canceled Bookings], [Total Bookings] )

Avg Lead Time = AVERAGE ( Bookings[lead_time] )

Realized Revenue = SUM ( Bookings[realized_revenue] )

Revenue Lost = SUM ( Bookings[lost_revenue] )

Stayed Nights = CALCULATE ( SUM ( Bookings[nights] ), Bookings[is_canceled] = 0 )

ADR = DIVIDE ( [Realized Revenue], [Stayed Nights] )

Revenue Lost % = DIVIDE ( [Revenue Lost], [Revenue Lost] + [Realized Revenue] )
```

## Visuals

| Visual | Fields |
| --- | --- |
| Cards | Total Bookings, Cancellation Rate, Avg Lead Time, ADR, Realized Revenue, Revenue Lost |
| Line and clustered column chart | X: `year_month`; columns: Total Bookings; line: Cancellation Rate |
| Column chart | X: `lead_band` (sort by lead time); Y: Cancellation Rate |
| Bar chart | Y: `channel`; X: Revenue Lost |
| Line chart | X: `month_num`; Y: ADR |
| Slicers | `hotel`, `season`, `channel` |

Tip: to show `lead_band` in the right order, select it and use **Sort by column → lead_band_order**.
