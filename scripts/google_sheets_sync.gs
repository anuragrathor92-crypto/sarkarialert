/**
 * Sarkari Alert — Rs. 0 Google Sheets Admin Dashboard Sync
 * 1. Open Google Sheets -> Extensions -> Apps Script
 * 2. Paste this code -> Save -> Run syncSarkariAlert()
 * 3. Optional: Add a Time-driven Trigger (Every hour) for 24x7 auto-sync.
 */
function syncSarkariAlert() {
  var url = "https://anuragrathor92-crypto.github.io/sarkarialert/data/public-search.json";
  var res = UrlFetchApp.fetch(url, { muteHttpExceptions: true });
  if (res.getResponseCode() !== 200) {
    throw new Error("Could not fetch Sarkari Alert JSON: HTTP " + res.getResponseCode());
  }
  var data = JSON.parse(res.getContentText());
  var items = Array.isArray(data) ? data : (data.items || data.records || []);
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName("Live_Posts") || ss.insertSheet("Live_Posts");
  sheet.clearContents();
  var rows = [["ID", "Title", "Category", "Department", "Last Date", "Apply Status", "URL", "Last Synced"]];
  var nowStr = Utilities.formatDate(new Date(), "Asia/Kolkata", "yyyy-MM-dd HH:mm IST");
  items.forEach(function (p) {
    rows.push([
      p.id || "",
      p.title || "",
      p.category || "",
      p.department || "",
      p.lastDate || "",
      p.applyStatus || p.applyLinkType || "",
      p.url || ("https://anuragrathor92-crypto.github.io/sarkarialert/posts/" + (p.id || "") + "/"),
      nowStr
    ]);
  });
  sheet.getRange(1, 1, rows.length, rows[0].length).setValues(rows);
  sheet.setFrozenRows(1);
}
