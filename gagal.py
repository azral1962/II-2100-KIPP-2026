import shutil
from datetime import datetime
from pathlib import Path
from file_lock import exclusive_file_lock
from llm import read_queue, write_queue, utc_now_text

def main() -> None:
    path = Path(__file__).resolve().with_name("antrian.csv")
    print("Memproses tiket berstatus GAGAL...")
    with exclusive_file_lock(path):
        backup = path.with_name(f"{path.name}.{datetime.now():%Y%m%d-%H%M%S-%f}.bak")
        shutil.copy2(path, backup)
        fields, rows = read_queue(path)
        count = 0
        for row in rows:
            if row["status"].strip().upper() == "GAGAL":
                row["status"] = "ANTRI"
                row["worker_id"] = ""
                row["updated_at"] = utc_now_text()
                count += 1
        write_queue(path, fields, rows)
    print(f"{count} tiket dikembalikan ke ANTRI. Cadangan: {backup}")


if __name__ == "__main__":
    main()
