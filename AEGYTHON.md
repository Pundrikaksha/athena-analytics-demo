# Aegython 2026: qualification and submission notes

Read on 2 Nov 2026 (IST) from the official pages:
- Unstop listing: https://unstop.com/hackathons/aegython-2026-aeglysai-1777958
- Organiser page (the organiser calls it authoritative): https://aeglysai.com/hackathons/
- Official repository to fork: https://github.com/shubh-techie/AeglysAI
- Official participant Google Form (linked from Unstop):
  https://docs.google.com/forms/d/e/1FAIpQLSeNfr0ah_d2yHuBzVZmRY87gkt7e4mGOcIB0IqczaUSl8ok9w/viewform
- Organiser contact: aegython@aeglysai.com

Nothing has been registered, forked or submitted. All of the steps below are for the user to do himself.

## Key facts and dates (IST)

| Item | Value |
|---|---|
| Unstop registration | opened 26 Oct 2026 00:00, **closes 6 Nov 2026 00:00** |
| Fee | Free |
| Team size | 1 to 4 (solo allowed) |
| Who can enter | Students, graduate students, early-career engineers, experienced practitioners, researchers. Age and geography: "TBA" in final terms |
| Organiser's own dates | All "TBA" (application, qualification, selection, build, video, rounds) |
| Prize (Unstop) | ₹30,000 / ₹20,000 / ₹10,000 (₹60,000 total) |
| Prize (organiser page) | "An existing planned USD $300 prize, with funding unconfirmed" |

⚠ The two prize statements disagree, and the organiser says its own page wins. Treat the cash as unconfirmed.

## Step 1: register (two places)

1. Register on Unstop before **6 Nov 2026 00:00 IST**.
2. Fill the official Google Form as well. Unstop says "only Google Form entries are considered for shortlisting".
   The form asks for: full name, contact email, mobile number with country code, GitHub username,
   GitHub profile URL, college/university, academic/professional status, preferred challenge track,
   participation format (solo/team), and acceptance of the event rules/terms and privacy notice.

## Step 2: mandatory individual qualification (before anyone may build)

From the organiser's Qualification Guide:

1. **Fork** https://github.com/shubh-techie/AeglysAI into your own GitHub account. You get no write access to the official repo.
2. **Clone your fork** locally. Keep secrets out of Git.
3. **Build and run** the A/B/C baseline using its README. Docker route: `./dev up`, `./dev health`, `./dev demo`.
   .NET route: `dotnet build`, `dotnet test`, `dotnet run --project src/AeglysAI.Api -- --urls http://localhost:5080`.
   Keep the commands and their output as evidence. Model D knowledge is not required.
4. Create a branch `qualification/<github-username>` in your fork. Never put an email, phone or ID in the branch name.
5. Write `community/qualification/<github-username>.md` covering: environment, OS, runtime,
   actual build/test results, the architecture and request/decision flow in your own words,
   **one technical observation** (and how you tested it), **one realistic improvement**, its engineering
   value, and **how you would validate it**. An upstream PR is not needed.
6. Push to your fork, then submit through the official Google Form: GitHub username, fork URL,
   qualification branch URL, qualification file URL and sanitised build-log URLs.
7. The organiser reviews. Qualification does not guarantee selection. Selected people build in their
   own forks on `hackathon/<name>` branches, or in a standalone repo ("standalone implementations are
   acceptable after mandatory AeglysAI qualification").

## Step 3: pick a challenge

Six problem statements: Smart Login Guardian, **Find the Anomaly**, API Traffic Watch, Explain My Security
Alert, Predict the Outage, AI for Everyday Life.

**Recommended for this repo: Find the Anomaly.** The organiser's minimum prototype is an "offline detector
with separate training/test inputs, declared thresholds and repeatable tests". This repo has exactly that:
tuning seeds 0–49 versus held-out seeds 1000–1199, declared thresholds (OI z > 5.0, IV/volume |z| > 3.5) and
15 unit tests. The domain is synthetic options-market measurements, which is a less usual angle than logs.
Fallback: AI for Everyday Life.

## Step 4: final project submission (Round 1)

Required items, with this repo's status:

| Requirement | Status |
|---|---|
| Team ID | Organiser issues after selection |
| Selected challenge | Find the Anomaly (proposed) |
| **Public** GitHub repo + frozen review commit or tag | ⛔ Repo is local only. Needs the user's yes to publish |
| README with reproducible setup | ✅ `README.md` |
| Demo video, at most 2 minutes (narrated or captioned screen recording) | ⛔ To record |
| Explanation of the AI/ML or intelligent technique | ✅ README "The intelligent part" |
| Testing or validation evidence | ✅ `tests/`, `scripts/evaluate_anomaly.py`, `docs/data/anomaly_evaluation.json` |
| Data/model attribution and licensing | ✅ README + MIT `LICENSE` |
| Known limitations | ✅ README |
| Deployed demo URL | Optional (`docs/` is GitHub Pages-ready) |

A slide deck alone is not enough; it must be a working prototype.

## Judging

Round 1 (technical screening, 100): working functionality 30, AI/ML or intelligent feature 25,
relevance and creativity 20, reproducibility 15, video clarity 10.

Round 2 (finalists, live on Google Meet: 5 min demo + 5 min Q&A, 100): live demo 35, technical
understanding 25, solution quality and safety 20, Q&A 15, presentation 5. Round 2 alone sets the ranking.

## Rules worth noting

- Original work, or attribute third-party code, data and models.
- Use only systems and data you are authorised to use. No security testing against real systems.
- No passwords, credentials, personal information or confidential material in public submissions.
- One active team per person. Roster changes need organiser approval.
