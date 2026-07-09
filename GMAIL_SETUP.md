# Gmail Drafts Setup (one-time, ~5 min)

This makes the 9 AM autopilot drop finished emails **straight into your Gmail
Drafts folder** — To / subject / body filled — so all you do is open Gmail and
hit **Send**. It only ever creates drafts; it never sends anything on its own.

## 1. Install the libraries
```
cd "C:\Projects with Code\business\opportunity-agent\backend"
pip install -r requirements.txt
```

## 2. Make a Google OAuth client (Desktop app)
1. Go to https://console.cloud.google.com/ and create a project (any name).
2. **APIs & Services → Library →** search **Gmail API →** Enable.
3. **APIs & Services → OAuth consent screen →** choose **External**, fill the
   required name/email, and add **yourself** as a **Test user** (your Gmail).
   (Leave it in "Testing" — you don't need Google verification for your own use.)
4. **APIs & Services → Credentials → Create Credentials → OAuth client ID →**
   Application type **Desktop app** → Create → **Download JSON**.
5. Save that file as:
   ```
   C:\Projects with Code\business\opportunity-agent\backend\gmail_credentials.json
   ```

## 3. Authorize once (opens your browser)
```
cd "C:\Projects with Code\business\opportunity-agent\backend"
python gmail_drafts.py
```
Sign in, approve the "create drafts" permission. It writes `gmail_token.json`.
That's it — the 9 AM task now runs headless and refreshes the token itself.

## Check it worked
```
python -c "import gmail_drafts; print('configured:', gmail_drafts.is_configured())"
```
Should print `configured: True`. Next run of `python morning_batch.py` (or the
9 AM task) will log **"Gmail drafts: ON"** and put the day's best emails in your
Drafts folder.

## Notes
- Scope is `gmail.compose` — create/read drafts only. It cannot send or read your
  inbox mail.
- `gmail_credentials.json` and `gmail_token.json` are secrets — don't commit them.
- Only leads that have a contact email become real drafts. To make "no website"
  businesses draftable, put their email in `targets.csv`.
- **Still ban-safe, still your call to send.** Drafts don't touch spam filters.
  The volume limit only matters when *you* hit send — from a personal Gmail,
  keep it to ~10–20/day at first, or use a warmed sending domain for real volume
  (see WEBSITE_MODE.md).
