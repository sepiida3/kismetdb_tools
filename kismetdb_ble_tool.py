import sqlite3
import argparse


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
        help="Remove BLE packets that have random address",
        action="store_true",
    )

    args = parser.parse_args()

    randoms, nonrandoms = parse_kismet(args.infile)

    print(f"{len(randoms)} packets with random address")
    print(f"{len(nonrandoms)} packets with public address")

    if args.purge:
        print(
            "Be aware this will permanently alter the kismetdb file.\nDo you wish to continue?"
        )
        proceed = input("[y/n] ")
        if proceed[0].lower() == "y":
            remove_randoms(args.infile, randoms)


def parse_kismet(input_filename):
    con = sqlite3.connect(input_filename)
    cur = con.cursor()

    results = cur.execute("SELECT rowid, packet FROM packets WHERE phyname = 'BTLE'")
    raw_datas = results.fetchall()
    con.close()

    randoms = []
    nonrandoms = []

    # magic bit is '{0:08b}'.format(sample[14])[1]
    for data in raw_datas:
        packet = data[1]
        rowid = data[0]
        packet_header = "{0:08b}".format(packet[14])
        if packet_header[1] == "1":
            randoms.append(rowid)
        else:
            nonrandoms.append(rowid)

    return randoms, nonrandoms


def remove_randoms(input_filename, randoms):
    con = sqlite3.connect(input_filename)
    cur = con.cursor()
    for random in randoms:
        cur.execute(f"DELETE FROM packets WHERE rowid = {random}")
    con.commit()
    print("Packets removed, vacuuming database...")
    con.execute("VACUUM")
    con.close()


if __name__ == "__main__":
    main()
