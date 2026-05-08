# Quiniela Mundial 2026 - Project Reference

## Owner
- Ricardo Millan (admin)
- GitHub: rmillan-git

## Tech Stack
- Backend: FastAPI (Python)
- Database: PostgreSQL
- Frontend: HTML + Bootstrap 5
- Deploy: Render.com (free tier)
- Local Dev: Podman + podman-compose

## World Cup 2026 Format
- 48 teams, 12 groups (A-L), 4 teams per group
- 104 total matches
- Host countries: USA, Canada, Mexico
- Start: June 11, 2026 | Final: July 19, 2026

## Rounds
1. Group Stage (12 groups)
2. Round of 32 (NEW - 24 group winners + 8 best 3rd place)
3. Round of 16
4. Quarterfinals
5. Semifinals
6. Final

## Scoring System
- Exact score: 9 points
- Correct winner/draw (wrong score): 7 points
- Wrong prediction: 0 points
- Knockout stage bonus: TBD

## Groups
| Group | Teams |
|-------|-------|
| A | Mexico, South Africa, South Korea, Czechia |
| B | Canada, Bosnia-Herzegovina, Qatar, Switzerland |
| C | Argentina, Chile, Peru, Ecuador |
| D | USA, Paraguay, Australia, Türkiye |
| E | Spain, Morocco, Senegal, Tunisia |
| F | Brazil, Colombia, Venezuela, Bolivia |
| G | France, Algeria, Ivory Coast, Cameroon |
| H | England, Jamaica, Panama, Honduras |
| I | Portugal, Poland, Ukraine, Georgia |
| J | Germany, Netherlands, Belgium, Serbia |
| K | Italy, Croatia, Slovenia, Albania |
| L | Japan, Saudi Arabia, Iran, Iraq |

## Timezones
- All times displayed in CST (Houston, TX)

## Participants
- Open registration - participants register themselves via web
- Admin (Ricardo) can approve/manage participants
- Each participant gets their own prediction profile

## Participant Data per User
- Name
- Email
- Registration date
- Predictions per match (home goals - away goals)
- Total points
- Points per round breakdown

## Project Structure (target)
quiniela-mundial-2026/
├── backend/
│   ├── main.py
│   ├── models.py
│   ├── database.py
│   ├── routes/
│   │   ├── auth.py
│   │   ├── participants.py
│   │   ├── matches.py
│   │   ├── predictions.py
│   │   └── leaderboard.py
│   └── requirements.txt
├── frontend/
│   ├── index.html        # leaderboard public
│   ├── register.html     # participant registration
│   ├── predictions.html  # enter/view predictions
│   ├── groups.html       # group stage tables
│   ├── bracket.html      # knockout bracket
│   └── admin.html        # admin panel (Ricardo only)
├── podman-compose.yml
├── render.yaml
└── CLAUDE.md

## Key Features
1. Open registration - anyone with the link can join
2. Predictions locked once match starts
3. Admin panel (Ricardo only) - enter real match results
4. Auto-calculate points after each result entered
5. Live leaderboard updated in real time
6. Group tables (G, W, D, L, GF, GA, GAvg, PTS)
7. Knockout bracket visualization
8. All times in CST (Houston, TX)
9. Mobile friendly (Bootstrap 5)

## Previous Pools Reference
- 2018 Russia: 15 participants
- 2022 Qatar: similar format
- Scoring system proven across both tournaments