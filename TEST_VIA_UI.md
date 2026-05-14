# Testing Regex Extractor via UI

The easiest and most realistic way to test the new Regex Extractor!

## Step 1: Start Backend Server

Open **Terminal 1** (PowerShell):

```powershell
cd C:\Users\sama\autoclean
.\venv\Scripts\Activate.ps1
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

**Keep this terminal open!** You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Application startup complete.
```

## Step 2: Start Frontend Server

Open **Terminal 2** (PowerShell):

```powershell
cd C:\Users\sama\autoclean\frontend
npm run dev
```

**Keep this terminal open!** You should see:
```
VITE v5.x.x  ready in xxx ms
➜  Local:   http://localhost:5173/
```

## Step 3: Open Browser

Open your browser and go to:
**http://localhost:5173**

## Step 4: Upload Test Dataset

1. **Click "Upload Dataset"** (or go to Upload page)

2. **Select the test file:**
   - Click "Choose File"
   - Navigate to: `C:\Users\sama\autoclean\data\storage\test_regex_patterns.csv`
   - Or use any CSV file with email, phone, date, URL columns

3. **Fill in the form:**
   - **Name**: "Test Regex Patterns" (or any name)
   - **Purpose**: Select "Rule Extraction"
   - **Modality**: Select "Tabular"
   - **Domain**: Select "General" (or any domain)

4. **Click "Upload"**

5. You'll be redirected to the dataset detail page

## Step 5: Extract Rules

1. On the dataset detail page, you'll see action cards

2. **Click "Extract Rules"** button (purple button with Play icon)

3. Wait for extraction to complete (should be fast - just a few seconds)

4. You'll see an alert: "Successfully extracted X rules!"

5. You'll be automatically redirected to the Rules page

## Step 6: View Extracted Rules

On the Rules page, you should see:

- **Email pattern rule** - for the `email` column
- **Phone pattern rule** - for the `phone` column  
- **Date ISO pattern rule** - for the `date_iso` column
- **Date US pattern rule** - for the `date_us` column
- **URL pattern rule** - for the `url` column
- **Zipcode pattern rule** - for the `zipcode` column

Each rule will show:
- **Predicate**: The regex pattern condition
- **Action**: The cleaning action
- **Confidence**: How confident the system is (0.0-1.0)
- **Explanation**: Human-readable description

## Expected Results

With `test_regex_patterns.csv`, you should get **6-7 rules** extracted.

### What to Look For:

✅ **Rules are extracted** - You see rules on the Rules page
✅ **Correct patterns detected** - Email, phone, date, URL patterns are found
✅ **High confidence** - Most rules should have confidence > 0.8
✅ **Clear explanations** - Each rule has a readable explanation
✅ **Fast extraction** - Should complete in < 5 seconds

### If Something Goes Wrong:

❌ **No rules extracted?**
   - Check browser console (F12) for errors
   - Check backend terminal for error messages
   - Verify the CSV file has data

❌ **Error message appears?**
   - Check backend terminal for detailed error
   - Make sure database is initialized: `python init_db.py`
   - Verify the file path is correct

❌ **Backend won't start?**
   - Make sure virtual environment is activated
   - Check that all dependencies are installed: `pip install -r backend/app/requirements.txt`

## Quick Test Checklist

- [ ] Backend server running on http://127.0.0.1:8000
- [ ] Frontend server running on http://localhost:5173
- [ ] Test CSV file exists: `data/storage/test_regex_patterns.csv`
- [ ] Dataset uploaded successfully
- [ ] "Extract Rules" button clicked
- [ ] Rules extracted (6-7 rules expected)
- [ ] Rules displayed on Rules page
- [ ] Each rule shows correct pattern type

## Next Steps After Testing

Once you confirm the Regex Extractor works:

1. ✅ Test with your own datasets
2. ✅ Try different file formats (CSV, Excel, JSON)
3. ✅ Test with larger datasets
4. ✅ Move on to building the next extractor (Mapping, ML, FD, etc.)

## Tips

- **Keep both terminals open** - Backend and frontend need to stay running
- **Check browser console** - Press F12 to see any JavaScript errors
- **Check backend logs** - The terminal running uvicorn shows all API calls and errors
- **Test with different data** - Try uploading datasets with different patterns

Happy testing! 🚀

