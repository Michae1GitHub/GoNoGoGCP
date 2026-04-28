## Explanation of the contents of the folder and stage 3

### Part 1

`stage3code` contains the data and code used in part 1 of stage 3.

#### Python files
The python files are used to convert the raw dataset downloaded into usable csv files for each table.

#### SQL file
`table_generation_1.sql` puts these data into the tables.

Specifically, table `user`, `passport`, `visa_req`, and `visa_cost` each have 1000+ lines each.

- `user` and `passport` tables use generated data
- the others use actual data


#### 3 Advance Sql Query Coding

Query 1 — Visa Cost Analysis
"Find destinations where the visa cost is cheaper than the average for that region"
For a specific user (user_id = 1), this query looks up all their passports, finds visa costs to various destinations, and filters to only show destinations where the cost is below the regional average. The correlated subquery recalculates the average cost per region dynamically for each row being evaluated. Results are sorted by region and cost, so the cheapest deals appear first.

Real-world use: "Show me budget-friendly visa destinations compared to similar countries nearby."

Query 2 — Regional Visa Accessibility
"By region, how long can the user stay on average, and how many destinations don't offer e-visas?"
This query combines two groups of destinations using UNION — places the user has already saved in trip plans, plus all visa-free destinations available to their passport (30+ day stays). It then groups everything by region and aggregates statistics like average max stay and count of non-e-visa destinations.

Real-world use: "Which regions are most accessible to me overall, and where might I face more paperwork?"

Query 3 — Visa Complexity Score
"Rank destinations by how complicated their visa process is"
For a specific passport (P1234567), this query builds a custom complexity score for each destination using a point system based on three factors — whether e-visa is available (+20 or +40), how expensive the visa is (+10 or +30), and how short the allowed stay is (+20 penalty). It also counts mandatory documents required via a correlated subquery, adding +10 if more than 3 documents are needed. Higher score = more complex visa process.

Real-world use: "Which destinations will be the most hassle to get a visa for, so I can plan accordingly?"

implementation: `AdvanceSQL_rewritten.sql`

results: `Stage3_1-5.md`
### Part 2

Part 2- Indexing.pdf contains the contents for part2.










### Special note
The revision for stage 2 is reflected in the pdf file in the stage3 folder. 













_(code run with:
mysql --local-infile=1 --protocol=TCP -h 127.0.0.1 -P 3306 -u root)_
