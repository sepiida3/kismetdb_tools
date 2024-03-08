import sqlite3
import argparse
import datetime


def main():
    parser = argparse.ArgumentParser(
        prog="kismetdb_ble_tool.py",
        description="Parse BLE entries from kismet capture",
    )

    parser.add_argument(
        "-i", "--in", dest="infile", required=True, help="input kismetdb file"
    )
    parser.add_argument(
        "-p",
        "--purge",
        required=False,
        help="remove BLE packets that have random address",
        action="store_true",
    )
    parser.add_argument(
        "-o",
        "--out",
        dest="outfile",
        required=False,
        help="file to write in wigle csv format",
    )

    args = parser.parse_args()

    randoms, publics = parse_kismet(args.infile)

    print(f"{len(randoms)} packets with random address")
    print(f"{len(publics)} packets with public address")

    if args.purge:
        print(
            "Be aware this will permanently alter the kismetdb file.\nDo you wish to continue?"
        )
        proceed = input("[y/n] ")
        if proceed[0].lower() == "y":
            remove_randoms(args.infile, randoms)

    if args.outfile:
        wigle_export(args.infile, args.outfile, publics)


def parse_kismet(input_filename):
    con = sqlite3.connect(input_filename)
    cur = con.cursor()

    results = cur.execute("SELECT rowid, packet FROM packets WHERE phyname = 'BTLE'")
    raw_datas = results.fetchall()
    con.close()

    randoms = []
    publics = []

    # magic bit is '{0:08b}'.format(sample[14])[1]
    for data in raw_datas:
        packet = data[1]
        rowid = data[0]
        packet_header = "{0:08b}".format(packet[14])
        if packet_header[1] == "1":
            randoms.append(rowid)
        else:
            publics.append(rowid)

    return randoms, publics


def remove_randoms(input_filename, randoms):
    con = sqlite3.connect(input_filename)
    cur = con.cursor()
    for random in randoms:
        cur.execute(f"DELETE FROM packets WHERE rowid = {random}")
    con.commit()
    print("Packets removed, vacuuming database...")
    con.execute("VACUUM")
    con.close()


def wigle_export(input_filename, output_filename, publics):
    con = sqlite3.connect(input_filename)
    cur = con.cursor()
    results = cur.execute("SELECT * FROM KISMET ORDER BY ROWID ASC")
    kismet_info = results.fetchall()
    app_release = f"Kismet{kismet_info[0][0].replace('.', '')}"
    release = f"{kismet_info[0][0]}.{str(kismet_info[0][1])}"

    pre_header = f"WigleWifi-1.4,appRelease={app_release},model=Kismet,release={release},device=kismet,display=kismet,board=kismet,brand=kismet\n"
    header = "MAC,SSID,AuthMode,FirstSeen,Channel,RSSI,CurrentLatitude,CurrentLongitude,AltitudeMeters,AccuracyMeters,Type\n"

    rows = []
    recorded = []

    for rowid in publics:
        results = cur.execute(
            f"SELECT ts_sec, sourcemac, lat, lon, alt, signal FROM packets where rowid = {rowid}"
        )
        packet_info = results.fetchall()

        mac = packet_info[0][1]
        ssid = ""
        auth_mode = "Misc"
        first_seen = datetime.datetime.fromtimestamp(
            packet_info[0][0], datetime.timezone.utc
        ).strftime("%Y-%m-%d %H:%M:%S")
        channel = ""
        rssi = packet_info[0][5]
        current_latitude = packet_info[0][2]
        current_longitude = packet_info[0][3]
        altitude_meters = packet_info[0][4]
        accuracy_meters = "0"
        the_type = "BLE"

        if current_latitude != 0 and current_longitude != 0:
            # one record per MAC per second is enough
            # probably not the best way to do this
            record = [first_seen, mac]
            if record not in recorded:
                row = f"{mac},{ssid},{auth_mode},{first_seen},{channel},{rssi},{current_latitude},{current_longitude},{altitude_meters},{accuracy_meters},{the_type}\n"
                rows.append(row)
                recorded.append(record)

    con.close()

    print(f"{len(rows)} rows to be written")

    with open(output_filename, "w") as f:
        f.write(pre_header)
        f.write(header)
        f.writelines(rows)

    print("Done!")


if __name__ == "__main__":
    main()
