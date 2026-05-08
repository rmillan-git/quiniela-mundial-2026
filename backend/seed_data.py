"""Seed correct 2026 World Cup teams and group-stage fixtures (ESPN/FIFA official draw)."""
from datetime import datetime, timezone
from database import engine, SessionLocal, Base
from models import Team, Match, Participant, Prediction
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

TEAMS = [
    # Group A
    ("Mexico", "A", "🇲🇽"),
    ("South Africa", "A", "🇿🇦"),
    ("South Korea", "A", "🇰🇷"),
    ("Czechia", "A", "🇨🇿"),
    # Group B
    ("Canada", "B", "🇨🇦"),
    ("Bosnia-Herzegovina", "B", "🇧🇦"),
    ("Qatar", "B", "🇶🇦"),
    ("Switzerland", "B", "🇨🇭"),
    # Group C
    ("Brazil", "C", "🇧🇷"),
    ("Morocco", "C", "🇲🇦"),
    ("Scotland", "C", "🏴󠁧󠁢󠁳󠁣󠁴󠁿"),
    ("Haiti", "C", "🇭🇹"),
    # Group D
    ("USA", "D", "🇺🇸"),
    ("Paraguay", "D", "🇵🇾"),
    ("Australia", "D", "🇦🇺"),
    ("Türkiye", "D", "🇹🇷"),
    # Group E
    ("Germany", "E", "🇩🇪"),
    ("Ecuador", "E", "🇪🇨"),
    ("Ivory Coast", "E", "🇨🇮"),
    ("Curaçao", "E", "🇨🇼"),
    # Group F
    ("Netherlands", "F", "🇳🇱"),
    ("Japan", "F", "🇯🇵"),
    ("Tunisia", "F", "🇹🇳"),
    ("Sweden", "F", "🇸🇪"),
    # Group G
    ("Belgium", "G", "🇧🇪"),
    ("Iran", "G", "🇮🇷"),
    ("Egypt", "G", "🇪🇬"),
    ("New Zealand", "G", "🇳🇿"),
    # Group H
    ("Spain", "H", "🇪🇸"),
    ("Uruguay", "H", "🇺🇾"),
    ("Saudi Arabia", "H", "🇸🇦"),
    ("Cape Verde", "H", "🇨🇻"),
    # Group I
    ("France", "I", "🇫🇷"),
    ("Senegal", "I", "🇸🇳"),
    ("Norway", "I", "🇳🇴"),
    ("Iraq", "I", "🇮🇶"),
    # Group J
    ("Argentina", "J", "🇦🇷"),
    ("Algeria", "J", "🇩🇿"),
    ("Austria", "J", "🇦🇹"),
    ("Jordan", "J", "🇯🇴"),
    # Group K
    ("Portugal", "K", "🇵🇹"),
    ("Colombia", "K", "🇨🇴"),
    ("Uzbekistan", "K", "🇺🇿"),
    ("DR Congo", "K", "🇨🇩"),
    # Group L
    ("England", "L", "🏴󠁧󠁢󠁥󠁮󠁧󠁿"),
    ("Croatia", "L", "🇭🇷"),
    ("Ghana", "L", "🇬🇭"),
    ("Panama", "L", "🇵🇦"),
]

def u(date_str, hour, minute=0):
    """Parse a UTC datetime from date string and hour."""
    y, m, d = [int(x) for x in date_str.split("-")]
    return datetime(y, m, d, hour, minute, tzinfo=timezone.utc)

# All kickoff times stored in UTC. ET (EDT) = UTC-4 in June/July 2026.
# Local Mexico times: CDT = UTC-5.
GROUP_MATCHES = [
    # ── GROUP A ──────────────────────────────────────────────────────────────
    (1,  "A", "Mexico",       "South Africa",  u("2026-06-11", 19),     "Estadio Azteca, Mexico City"),
    (2,  "A", "South Korea",  "Czechia",        u("2026-06-12",  2),     "Estadio Akron, Guadalajara"),
    (3,  "A", "Czechia",      "South Africa",   u("2026-06-18", 16),     "Mercedes-Benz Stadium, Atlanta"),
    (4,  "A", "Mexico",       "South Korea",    u("2026-06-19",  3),     "Estadio Akron, Guadalajara"),
    (5,  "A", "Mexico",       "Czechia",        u("2026-06-24", 23),     "Estadio Azteca, Mexico City"),
    (6,  "A", "South Africa", "South Korea",    u("2026-06-24", 23),     "NRG Stadium, Houston"),
    # ── GROUP B ──────────────────────────────────────────────────────────────
    (7,  "B", "Canada",             "Bosnia-Herzegovina", u("2026-06-12", 19), "BMO Field, Toronto"),
    (8,  "B", "Qatar",              "Switzerland",        u("2026-06-13", 19), "Levi's Stadium, San Jose"),
    (9,  "B", "Switzerland",        "Bosnia-Herzegovina", u("2026-06-18", 19), "SoFi Stadium, Los Angeles"),
    (10, "B", "Canada",             "Qatar",              u("2026-06-18", 22), "BC Place, Vancouver"),
    (11, "B", "Canada",             "Switzerland",        u("2026-06-24", 23), "MetLife Stadium, East Rutherford"),
    (12, "B", "Bosnia-Herzegovina", "Qatar",              u("2026-06-24", 23), "AT&T Stadium, Dallas"),
    # ── GROUP C ──────────────────────────────────────────────────────────────
    (13, "C", "Brazil",   "Morocco",  u("2026-06-13", 22), "MetLife Stadium, East Rutherford"),
    (14, "C", "Haiti",    "Scotland", u("2026-06-14",  1), "Gillette Stadium, Boston"),
    (15, "C", "Scotland", "Morocco",  u("2026-06-19", 22), "Gillette Stadium, Boston"),
    (16, "C", "Brazil",   "Haiti",    u("2026-06-20",  1), "Lincoln Financial Field, Philadelphia"),
    (17, "C", "Scotland", "Brazil",   u("2026-06-24", 22), "Hard Rock Stadium, Miami"),
    (18, "C", "Morocco",  "Haiti",    u("2026-06-24", 22), "Mercedes-Benz Stadium, Atlanta"),
    # ── GROUP D ──────────────────────────────────────────────────────────────
    (19, "D", "USA",       "Paraguay",  u("2026-06-13",  1), "SoFi Stadium, Los Angeles"),
    (20, "D", "Australia", "Türkiye",   u("2026-06-14",  4), "BC Place, Vancouver"),
    (21, "D", "USA",       "Australia", u("2026-06-19", 19), "Lumen Field, Seattle"),
    (22, "D", "Türkiye",   "Paraguay",  u("2026-06-20",  4), "Levi's Stadium, San Jose"),
    (23, "D", "Türkiye",   "USA",       u("2026-06-26",  2), "SoFi Stadium, Los Angeles"),
    (24, "D", "Paraguay",  "Australia", u("2026-06-26",  2), "Levi's Stadium, San Jose"),
    # ── GROUP E ──────────────────────────────────────────────────────────────
    (25, "E", "Germany",     "Curaçao",     u("2026-06-14", 17), "NRG Stadium, Houston"),
    (26, "E", "Ivory Coast", "Ecuador",     u("2026-06-14", 23), "Lincoln Financial Field, Philadelphia"),
    (27, "E", "Germany",     "Ivory Coast", u("2026-06-20", 20), "BMO Field, Toronto"),
    (28, "E", "Ecuador",     "Curaçao",     u("2026-06-21",  0), "Arrowhead Stadium, Kansas City"),
    (29, "E", "Ecuador",     "Germany",     u("2026-06-25", 20), "MetLife Stadium, East Rutherford"),
    (30, "E", "Curaçao",     "Ivory Coast", u("2026-06-25", 20), "Lincoln Financial Field, Philadelphia"),
    # ── GROUP F ──────────────────────────────────────────────────────────────
    (31, "F", "Netherlands", "Japan",       u("2026-06-14", 20), "AT&T Stadium, Dallas"),
    (32, "F", "Sweden",      "Tunisia",     u("2026-06-15",  2), "Estadio BBVA, Monterrey"),
    (33, "F", "Netherlands", "Sweden",      u("2026-06-20", 17), "NRG Stadium, Houston"),
    (34, "F", "Tunisia",     "Japan",       u("2026-06-21",  4), "Estadio BBVA, Monterrey"),
    (35, "F", "Japan",       "Sweden",      u("2026-06-25", 23), "AT&T Stadium, Dallas"),
    (36, "F", "Tunisia",     "Netherlands", u("2026-06-25", 23), "Arrowhead Stadium, Kansas City"),
    # ── GROUP G ──────────────────────────────────────────────────────────────
    (37, "G", "Belgium",     "Egypt",        u("2026-06-15", 22), "Lumen Field, Seattle"),
    (38, "G", "Iran",        "New Zealand",  u("2026-06-16",  4), "SoFi Stadium, Los Angeles"),
    (39, "G", "Belgium",     "Iran",         u("2026-06-21", 19), "SoFi Stadium, Los Angeles"),
    (40, "G", "New Zealand", "Egypt",        u("2026-06-22",  1), "BC Place, Vancouver"),
    (41, "G", "Egypt",       "Iran",         u("2026-06-27",  3), "Lumen Field, Seattle"),
    (42, "G", "New Zealand", "Belgium",      u("2026-06-27",  3), "BC Place, Vancouver"),
    # ── GROUP H ──────────────────────────────────────────────────────────────
    (43, "H", "Spain",        "Cape Verde",   u("2026-06-15", 17), "Mercedes-Benz Stadium, Atlanta"),
    (44, "H", "Saudi Arabia", "Uruguay",      u("2026-06-15", 22), "Hard Rock Stadium, Miami"),
    (45, "H", "Spain",        "Saudi Arabia", u("2026-06-21", 16), "Mercedes-Benz Stadium, Atlanta"),
    (46, "H", "Uruguay",      "Cape Verde",   u("2026-06-21", 22), "Hard Rock Stadium, Miami"),
    (47, "H", "Cape Verde",   "Saudi Arabia", u("2026-06-27",  0), "NRG Stadium, Houston"),
    (48, "H", "Uruguay",      "Spain",        u("2026-06-27",  0), "Estadio Akron, Guadalajara"),
    # ── GROUP I ──────────────────────────────────────────────────────────────
    (49, "I", "France",  "Senegal", u("2026-06-16", 19), "MetLife Stadium, East Rutherford"),
    (50, "I", "Iraq",    "Norway",  u("2026-06-16", 22), "Gillette Stadium, Boston"),
    (51, "I", "France",  "Iraq",    u("2026-06-22", 21), "Lincoln Financial Field, Philadelphia"),
    (52, "I", "Norway",  "Senegal", u("2026-06-23",  0), "MetLife Stadium, East Rutherford"),
    (53, "I", "Norway",  "France",  u("2026-06-26", 19), "Gillette Stadium, Boston"),
    (54, "I", "Senegal", "Iraq",    u("2026-06-26", 19), "BMO Field, Toronto"),
    # ── GROUP J ──────────────────────────────────────────────────────────────
    (55, "J", "Argentina", "Algeria",  u("2026-06-17",  1), "Arrowhead Stadium, Kansas City"),
    (56, "J", "Austria",   "Jordan",   u("2026-06-17",  4), "Levi's Stadium, San Jose"),
    (57, "J", "Argentina", "Austria",  u("2026-06-22", 17), "AT&T Stadium, Dallas"),
    (58, "J", "Jordan",    "Algeria",  u("2026-06-23",  3), "Levi's Stadium, San Jose"),
    (59, "J", "Algeria",   "Austria",  u("2026-06-28",  2), "Arrowhead Stadium, Kansas City"),
    (60, "J", "Jordan",    "Argentina",u("2026-06-28",  2), "AT&T Stadium, Dallas"),
    # ── GROUP K ──────────────────────────────────────────────────────────────
    (61, "K", "Portugal",   "DR Congo",   u("2026-06-17", 17), "NRG Stadium, Houston"),
    (62, "K", "Uzbekistan", "Colombia",   u("2026-06-18",  2), "Estadio Azteca, Mexico City"),
    (63, "K", "Portugal",   "Uzbekistan", u("2026-06-23", 17), "NRG Stadium, Houston"),
    (64, "K", "Colombia",   "DR Congo",   u("2026-06-24",  2), "Estadio Akron, Guadalajara"),
    (65, "K", "Colombia",   "Portugal",   u("2026-06-27", 23, 30), "Hard Rock Stadium, Miami"),
    (66, "K", "DR Congo",   "Uzbekistan", u("2026-06-27", 23, 30), "Mercedes-Benz Stadium, Atlanta"),
    # ── GROUP L ──────────────────────────────────────────────────────────────
    (67, "L", "England", "Croatia", u("2026-06-17", 20), "AT&T Stadium, Dallas"),
    (68, "L", "Ghana",   "Panama",  u("2026-06-17", 23), "BMO Field, Toronto"),
    (69, "L", "England", "Ghana",   u("2026-06-23", 20), "Gillette Stadium, Boston"),
    (70, "L", "Panama",  "Croatia", u("2026-06-23", 23), "BMO Field, Toronto"),
    (71, "L", "Panama",  "England", u("2026-06-27", 21), "MetLife Stadium, East Rutherford"),
    (72, "L", "Croatia", "Ghana",   u("2026-06-27", 21), "Lincoln Financial Field, Philadelphia"),
]


def seed(reset=False):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    if reset:
        db.query(Prediction).delete()
        db.query(Match).delete()
        db.query(Team).delete()
        db.query(Participant).filter_by(is_admin=False).delete()
        db.commit()
        print("Existing data cleared.")

    # Admin participant
    if not db.query(Participant).filter_by(email="millan.ricardo@gmail.com").first():
        admin = Participant(
            name="Ricardo Millan",
            email="millan.ricardo@gmail.com",
            hashed_password=pwd_context.hash("admin123"),
            is_admin=True,
            is_approved=True,
        )
        db.add(admin)
        db.flush()

    # Teams
    team_map = {}
    for name, group, flag in TEAMS:
        t = db.query(Team).filter_by(name=name).first()
        if not t:
            t = Team(name=name, group=group, flag_emoji=flag)
            db.add(t)
            db.flush()
        team_map[name] = t

    # Matches
    for num, group, home_name, away_name, kickoff, venue in GROUP_MATCHES:
        if not db.query(Match).filter_by(match_number=num).first():
            m = Match(
                match_number=num,
                round="group_stage",
                group=group,
                home_team_id=team_map[home_name].id,
                away_team_id=team_map[away_name].id,
                kickoff_utc=kickoff,
                venue=venue,
            )
            db.add(m)

    # Knockout stage placeholder matches (official 2026 bracket)
    KO_MATCHES = [
        # Round of 32 (matches 73-88)
        (73,  "round_of_32", None, "2° Grupo A",            "2° Grupo B",             u("2026-06-29", 20), "MetLife Stadium, East Rutherford"),
        (74,  "round_of_32", None, "1° Grupo E",            "Mejor 3° (A/B/C/D/F)",   u("2026-06-29", 23), "NRG Stadium, Houston"),
        (75,  "round_of_32", None, "1° Grupo F",            "2° Grupo C",             u("2026-06-30", 20), "AT&T Stadium, Dallas"),
        (76,  "round_of_32", None, "1° Grupo C",            "2° Grupo F",             u("2026-06-30", 23), "Levi's Stadium, San Jose"),
        (77,  "round_of_32", None, "1° Grupo I",            "Mejor 3° (C/D/F/G/H)",   u("2026-07-01", 20), "Gillette Stadium, Boston"),
        (78,  "round_of_32", None, "2° Grupo E",            "2° Grupo I",             u("2026-07-01", 23), "SoFi Stadium, Los Angeles"),
        (79,  "round_of_32", None, "1° Grupo A",            "Mejor 3° (C/E/F/H/I)",   u("2026-07-02", 20), "Arrowhead Stadium, Kansas City"),
        (80,  "round_of_32", None, "1° Grupo L",            "Mejor 3° (E/H/I/J/K)",   u("2026-07-02", 23), "BC Place, Vancouver"),
        (81,  "round_of_32", None, "1° Grupo D",            "Mejor 3° (B/E/F/I/J)",   u("2026-07-03", 20), "Lumen Field, Seattle"),
        (82,  "round_of_32", None, "1° Grupo G",            "Mejor 3° (A/E/H/I/J)",   u("2026-07-03", 23), "Hard Rock Stadium, Miami"),
        (83,  "round_of_32", None, "2° Grupo K",            "2° Grupo L",             u("2026-07-04", 20), "Lincoln Financial Field, Philadelphia"),
        (84,  "round_of_32", None, "1° Grupo H",            "2° Grupo J",             u("2026-07-04", 23), "Mercedes-Benz Stadium, Atlanta"),
        (85,  "round_of_32", None, "1° Grupo B",            "Mejor 3° (E/F/G/I/J)",   u("2026-07-05", 20), "BMO Field, Toronto"),
        (86,  "round_of_32", None, "1° Grupo J",            "2° Grupo H",             u("2026-07-05", 23), "Estadio Azteca, Mexico City"),
        (87,  "round_of_32", None, "1° Grupo K",            "Mejor 3° (D/E/I/J/L)",   u("2026-07-06", 20), "Rose Bowl, Pasadena"),
        (88,  "round_of_32", None, "2° Grupo D",            "2° Grupo G",             u("2026-07-06", 23), "Estadio Akron, Guadalajara"),
        # Round of 16 (matches 89-96)
        (89,  "round_of_16", None, "Ganador P73",           "Ganador P74",            u("2026-07-08", 20), "MetLife Stadium, East Rutherford"),
        (90,  "round_of_16", None, "Ganador P75",           "Ganador P76",            u("2026-07-08", 23), "AT&T Stadium, Dallas"),
        (91,  "round_of_16", None, "Ganador P77",           "Ganador P78",            u("2026-07-09", 20), "NRG Stadium, Houston"),
        (92,  "round_of_16", None, "Ganador P79",           "Ganador P80",            u("2026-07-09", 23), "SoFi Stadium, Los Angeles"),
        (93,  "round_of_16", None, "Ganador P81",           "Ganador P82",            u("2026-07-10", 20), "Hard Rock Stadium, Miami"),
        (94,  "round_of_16", None, "Ganador P83",           "Ganador P84",            u("2026-07-10", 23), "Mercedes-Benz Stadium, Atlanta"),
        (95,  "round_of_16", None, "Ganador P85",           "Ganador P86",            u("2026-07-11", 20), "Estadio Azteca, Mexico City"),
        (96,  "round_of_16", None, "Ganador P87",           "Ganador P88",            u("2026-07-11", 23), "Levi's Stadium, San Jose"),
        # Quarterfinals (matches 97-100)
        (97,  "qf", None, "Ganador P89", "Ganador P90",  u("2026-07-14", 20), "MetLife Stadium, East Rutherford"),
        (98,  "qf", None, "Ganador P91", "Ganador P92",  u("2026-07-14", 23), "SoFi Stadium, Los Angeles"),
        (99,  "qf", None, "Ganador P93", "Ganador P94",  u("2026-07-15", 20), "AT&T Stadium, Dallas"),
        (100, "qf", None, "Ganador P95", "Ganador P96",  u("2026-07-15", 23), "NRG Stadium, Houston"),
        # Semifinals (matches 101-102)
        (101, "sf", None, "Ganador P97", "Ganador P98",  u("2026-07-17", 22), "MetLife Stadium, East Rutherford"),
        (102, "sf", None, "Ganador P99", "Ganador P100", u("2026-07-18", 22), "AT&T Stadium, Dallas"),
        # Final (match 104)
        (104, "final", None, "Ganador P101", "Ganador P102", u("2026-07-19", 20), "MetLife Stadium, East Rutherford"),
    ]

    for num, round_, group_, home_ph, away_ph, kickoff, venue in KO_MATCHES:
        if not db.query(Match).filter_by(match_number=num).first():
            m = Match(
                match_number=num,
                round=round_,
                group=group_,
                home_team_placeholder=home_ph,
                away_team_placeholder=away_ph,
                kickoff_utc=kickoff,
                venue=venue,
            )
            db.add(m)

    db.commit()
    db.close()
    print(f"Seed complete. {len(GROUP_MATCHES)} group stage + {len(KO_MATCHES)} knockout matches loaded.")


if __name__ == "__main__":
    import sys
    reset = "--reset" in sys.argv
    seed(reset=reset)
