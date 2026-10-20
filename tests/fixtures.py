"""Synthetic CSV in the exact format of the real SignalConso file. FOR TESTS ONLY.

Header and value formats copy the real file (id;category;subcategories;Date;...;dep_code;...).
Volumes, sectors and trends are invented: they only exist to check the pipeline and the app.
The project's real data is downloaded with `python scripts/download_data.py`.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

OLD_SECTORS = ["AchatInternet", "DemarchageAbusif", "AchatMagasin", "TravauxRenovations",
               "VoyageLoisirs", "TelephonieFaiMedias", "BanqueAssuranceMutuelle", "CafeRestaurant"]
NEW_SECTORS = ["Internet", "Sante", "ProduitsObjets"]          # appear from 2023 on; one is unmapped
SUB_PATHS = ["Un_influenceur,Linfluenceur_nindique_pas_le_caractere_commercial", "Colis_non_recu",
             "Produit,Produit_non_conforme", "Appel_non_sollicite"]
STATUSES = ["Infonde", "MalAttribue", "PromesseAction", "NonConsulte", "ConsulteIgnore"]
DEPTS = ["75", "13", "69", "59", "33", "31", "06", "44", "67", "2A", "974", "92", "93", "988"]
DEPT_WEIGHTS = np.array([14, 9, 8, 8, 6, 6, 5, 5, 4, 1, 2, 7, 7, 1], dtype=float)
HEADER = ["id", "category", "subcategories", "Date", "contactAgreement", "status", "forwardToReponseConso",
          "tags", "Signalement Transmis", "Signalement Lu par l'entreprise",
          "Signalement ayant reçu une réponse", "dep_name", "dep_code", "Code Officiel Région",
          "Nom Officiel Région"]


def make_csv(path: Path, n: int = 20_000, seed: int = 7) -> Path:
    """Write n valid rows plus known defects: 40 bad dates, 10 future, 10 pre-launch, 60 blank
    categories, 300 missing départements and 25 duplicated ids."""
    rng = np.random.default_rng(seed)
    start, end = pd.Timestamp("2018-11-25"), pd.Timestamp("2026-10-10")
    days = (end - start).days
    dates = pd.Series(start + pd.to_timedelta((rng.beta(2.2, 1.0, n) * days).astype(int), unit="D"))
    december = (rng.random(n) < 0.15) & (dates.dt.year < 2026).to_numpy()
    dates[december] = dates[december].map(lambda d: d.replace(month=12, day=min(d.day, 28)))

    old = rng.choice(OLD_SECTORS, n, p=np.array([30, 20, 10, 10, 8, 8, 8, 6]) / 100)
    new = rng.choice(NEW_SECTORS, n)
    category = np.where((dates.dt.year >= 2023).to_numpy() & (rng.random(n) < 0.5), new, old)
    dept = rng.choice(DEPTS, n, p=DEPT_WEIGHTS / DEPT_WEIGHTS.sum())
    forwarded = (rng.random(n) < 0.9).astype(int)
    read = forwarded * (rng.random(n) < 0.7).astype(int)
    answered = read * (rng.random(n) < 0.6).astype(int)

    df = pd.DataFrame({
        "id": [f"a8c8b83a-ff4c-454e-aea4-{i:012d}" for i in range(n)],
        "category": category,
        "subcategories": rng.choice(SUB_PATHS, n),
        "Date": dates.dt.strftime("%Y-%m-%d"),
        "contactAgreement": rng.integers(0, 2, n),
        "status": rng.choice(STATUSES, n),
        "forwardToReponseConso": 0,
        "tags": "",
        "Signalement Transmis": forwarded,
        "Signalement Lu par l'entreprise": read,
        "Signalement ayant reçu une réponse": answered,
        "dep_name": "x",
        "dep_code": dept,
        "Code Officiel Région": 11,
        "Nom Officiel Région": "x",
    })[HEADER]
    df.loc[rng.choice(n, 40, replace=False), "Date"] = "n/a"
    df.loc[rng.choice(n, 10, replace=False), "Date"] = "2099-01-01"
    df.loc[rng.choice(n, 10, replace=False), "Date"] = "2010-01-01"
    df.loc[rng.choice(n, 60, replace=False), "category"] = None
    df.loc[rng.choice(n, 300, replace=False), "dep_code"] = None
    df = pd.concat([df, df.iloc[:25]], ignore_index=True)       # 25 duplicated ids

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, sep=";", index=False, encoding="utf-8")
    return path
