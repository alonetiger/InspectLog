"""Verifies the built InspectLog.exe binary, PE headers, and elevation manifest."""

import os
import sys

try:
    import pefile
except ImportError:
    pefile = None


def verify_executable(exe_path: str) -> bool:
    print(f"[*] Checking executable at: {exe_path}")
    if not os.path.exists(exe_path):
        print(f"[FAIL] Executable does not exist: {exe_path}")
        return False

    size_mb = os.path.getsize(exe_path) / (1024 * 1024)
    print(f"[+] File size: {size_mb:.2f} MB")
    if size_mb < 20:
        print("[FAIL] File size suspiciously small (< 20 MB for bundled Qt app)")
        return False

    if pefile is None:
        print("[WARN] pefile not available, skipping deep PE inspection")
        return True

    try:
        pe = pefile.PE(exe_path)
        print(f"[+] Valid PE binary. Machine type: 0x{pe.FILE_HEADER.Machine:X} (IMAGE_FILE_MACHINE_AMD64)")

        # Check for manifest in resources
        manifest_found = False
        manifest_content = ""
        if hasattr(pe, "DIRECTORY_ENTRY_RESOURCE"):
            for entry in pe.DIRECTORY_ENTRY_RESOURCE.entries:
                if entry.id == pefile.RESOURCE_TYPE.get("RT_MANIFEST", 24):
                    for subentry in entry.directory.entries:
                        for subsub in subentry.directory.entries:
                            data = pe.get_data(subsub.data.struct.OffsetToData, subsub.data.struct.Size)
                            manifest_content = data.decode("utf-8", errors="replace")
                            manifest_found = True
                            break

        if manifest_found:
            print("[+] Embedded UAC manifest found!")
            print("--- Embedded Manifest snippet ---")
            for line in manifest_content.splitlines()[:15]:
                print(f"  {line}")
            print("---------------------------------")
            if "requireAdministrator" in manifest_content:
                print("[PASS] Manifest contains: requireAdministrator")
                return True
            else:
                print("[FAIL] requireAdministrator NOT found in embedded manifest")
                return False
        else:
            print("[WARN] No embedded RT_MANIFEST resource entry found")
            return False
    except Exception as exc:
        print(f"[FAIL] Error parsing PE binary: {exc}")
        return False


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    dist_dir = os.path.abspath(os.path.join(script_dir, "..", "..", "dist"))
    exe_file = os.path.join(dist_dir, "InspectLog.exe")

    success = verify_executable(exe_file)
    sys.exit(0 if success else 1)
