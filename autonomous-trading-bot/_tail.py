import pathlib

for name, p in (("TESTNET", "autonomous-trading-bot/logs/turbo_err.log"),
                ("LIVE", "atb-live/logs/turbo_err.log")):
    lines = pathlib.Path(p).read_text(encoding="utf-8", errors="replace").splitlines()[-400:]
    rounds = [ln for ln in lines if "round " in ln and "monitor=" in ln]
    risk = [ln for ln in lines if "dang " in ln and "moi " in ln]
    hb = [ln for ln in lines if "hoi dong" in ln]
    print(name, "| round cuoi:", rounds[-1][:19] if rounds else "?")
    print("   ", risk[-1][:140] if risk else "(khong co dong SKIP_RISK)")
    print("   ", hb[-1][:140] if hb else "(khong co dong hoi dong)")
