import sqlite3
import json
import argparse
import simplekml


def main():
    parser = argparse.ArgumentParser(
        prog="kismetdb_rtl_extract.py",
        description="Parse rtl433 entries from kismet capture",
    )

    parser.add_argument(
        "-i", "--in", dest="infile", required=True, help="input kismetdb file"
    )
    parser.add_argument(
        "-o", "--out", dest="outfile", required=False, help="file to write"
    )
    parser.add_argument(
        "-d",
        "--devices",
        required=False,
        help="list all unique devices seen",
        action="store_true",
    )
    parser.add_argument(
        "-k",
        "--kml",
        required=False,
        help="write kml file instead of default json",
        action="store_true",
    )
    args = parser.parse_args()

    rtl_signals = parse_kismet(args.infile)

    print(f"Total of {len(rtl_signals)} rtl433 signals found")

    devices = get_devices(rtl_signals)
    print(f"{len(devices)} unique devices seen")
    if args.devices:
        for device in devices:
            print(f"{device[0]} {device[1]}")

    if args.outfile:
        if args.kml:
            write_kml(args.infile, args.outfile, rtl_signals)
        else:
            with open(args.outfile, "w") as f:
                json.dump(rtl_signals, f)

        print(f"Wrote signals to {args.outfile}")


def parse_kismet(input_filename):
    con = sqlite3.connect(input_filename)
    cur = con.cursor()

    results = cur.execute("SELECT lat, lon, json FROM data WHERE phyname = 'RFSENSOR'")
    raw_datas = results.fetchall()

    rtl_signals = []

    for raw_data in raw_datas:
        rtl_signal = json.loads(raw_data[-1])
        rtl_signal["lat"] = raw_data[0]
        rtl_signal["long"] = raw_data[1]
        if "id" not in rtl_signal:
            rtl_signal["id"] = ""

        rtl_signals.append(rtl_signal)

    return rtl_signals


def get_devices(rtl_signals):
    unique_devices = []

    for signal in rtl_signals:
        device = (signal["model"], signal["id"])
        if device not in unique_devices:
            unique_devices.append(device)

    return unique_devices


def write_kml(infile, outfile, rtl_signals):
    kml = simplekml.Kml(name=infile)

    for signal in rtl_signals:
        pnt = kml.newpoint()
        pnt.name = signal["model"]
        pnt.description = (
            f"id : {signal['id']}\nrssi : {signal['rssi']}\nmod : {signal['mod']}"
        )
        pnt.coords = [(signal["long"], signal["lat"])]
        pnt.style.iconstyle.icon.href = (
            "http://maps.gstatic.com/mapfiles/ms2/micons/green.png"
        )

    kml.save(outfile)


if __name__ == "__main__":
    main()
