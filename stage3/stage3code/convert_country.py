import csv


def norm(s: str) -> str:
    return " ".join(s.strip().lower().split())





input = "data/countries_of_the_world.csv"
output = "data/country_sql.csv"
iso = "data/att_country_codes.csv"


isos = {}
with open(iso, "r", encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)
    
    for row in reader:
        isos[norm(row["country"])] = {"iso2": row["iso2"].strip(), "iso3": row["iso3"].strip(),}





rows_written = 0
unmatched = []
with open(input, "r", encoding="utf-8-sig", newline="") as infile, \
     open(output, "w", encoding="utf-8", newline="") as outfile:

    reader = csv.DictReader(infile)
    writer = csv.writer(outfile)

    writer.writerow([
        "country_name", "region_name", "iso_alpha2", "iso_alpha3", "iso_numeric"])

    seen = set()

    for row in reader:
        raw_country = row["Country"].strip()
        raw_region = row["Region"].strip()
        


        key = norm(raw_country)
        
		

        if key == "antigua & barbuda":
            key = "antigua and barbuda"
        elif key == "bahamas, the":
            key = "bahamas"
        elif key == "bosnia & herzegovina":
            key = "bosnia and herzegovina"
        elif key == "british virgin is.":
            key = "british virgin islands"
        elif key == "burma":
            key = "burma (myanmar)"
        elif key == "central african rep.":
            key = "central african republic"
        elif key == "congo, dem. rep.":
            key = "democratic republic of the congo"
            
        elif key == "congo, repub. of the ":
            key = "republic of the congo"
            
        elif key == "cote d'ivoire":
            key = "ivory coast (côte d'ivoire)"
        elif key == "east timor":
            key = "timor-leste (east timor)"
        elif key == "gambia, the":
            key = "gambia"
        elif key == "gaza strip":
            key = "palestine"
        elif key == "korea, north":
            key = "north korea"
        elif key == "korea, south":
            key = "south korea"
        elif key == "micronesia, fed. st.":
            key = "micronesia"
        elif key == "n. mariana islands":
            key = "northern mariana islands"
        elif key == "reunion":
            key = "reunion island"
        elif key == "saint kitts & nevis":
            key = "saint kitts and nevis"
        elif key == "st pierre & miquelon":
            key = "saint pierre and miquelon"
        elif key == "sao tome & principe":
            key = "sao tome and principe"
        elif key == "tonga":
            key = "tonga islands"
        elif key == "trinidad & tobago":
            key = "trinidad and tobago"
        elif key == "turks & caicos is":
            key = "turks and caicos islands"
        elif key == "virgin islands":
            key = "us virgin islands"
        elif key == "west bank":
            key = "palestine"













        isod = isos.get(key)
        if not isod:
            unmatched.append(raw_country)
            continue

        if isod["iso3"] in seen:
            continue

        writer.writerow([raw_country, raw_region, isod["iso2"], isod["iso3"], ""])
        seen.add(isod["iso3"])
        rows_written += 1


if unmatched:
    print("\nUnmatched????")
    for name in unmatched:
        print("-", name)