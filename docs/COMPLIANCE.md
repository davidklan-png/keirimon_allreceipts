# Compliance Reference

## 事務処理規程（電子取引データ保存用）

This document satisfies the 電子帳簿保存法 authenticity requirement for small GK without a certified timestamp service. File this with your accountant and retain permanently.

---

**電子取引データの保存に関する事務処理規程**

制定日：　　　年　　月　　日
会社名：　　　　　　　　合同会社
代表者：

**第1条（目的）**
本規程は、電子帳簿保存法第7条に基づき、電子取引データの保存方法に関する事務処理手続きを定めることを目的とする。

**第2条（適用範囲）**
本規程は、取引先から電子的方法（電子メール、ウェブサイト等）で受領したすべての請求書、領収書、納品書その他の取引情報の電磁的記録に適用する。

**第3条（保存責任者）**
電子取引データの保存責任者は代表社員とし、保存業務を一元管理する。

**第4条（保存方法）**
1. 電子取引データは受領後速やかに、所定の電子保存システム（領収書管理アプリケーション）を用いてPDFファイルとして保存する。
2. ファイル名は「YYYYMMDD_カテゴリコード_連番_取引先名_金額.pdf」の形式とし、取引年月日・金額・取引先が特定できるよう命名する。
3. 保存先は指定フォルダー（AllReceipts/FY{年度}/{月}/）とし、会計年度・月別に整理する。

**第5条（訂正・削除の禁止）**
1. 保存した電子取引データの訂正・削除は原則として禁止する。
2. やむを得ず訂正が必要な場合は、保存責任者の承認のもと、修正内容をシステムの監査ログに記録した上で行う。

**第6条（検索機能の確保）**
保存した電子取引データは、取引年月日、取引金額、取引先名称を条件として検索できる状態を維持する。

**第7条（保存期間）**
電子取引データは法人税法の規定に従い、当該取引の属する事業年度終了の日の翌日から7年間保存する。

**第8条（バックアップ）**
保存データは定期的に外部媒体またはクラウドストレージにバックアップを作成し、データの消失を防止する。

---

## 電帳法 Compliance Checklist

Run through this at each fiscal year-end:

- [ ] All digitally-received receipts (AMEX, Anthropic, OpenAI, Amazon etc.) are stored as PDF — none printed and kept as paper-only
- [ ] All filed PDFs are searchable by date, amount, and vendor via the app's search screen
- [ ] Audit log (`audit.log`) is intact and append-only — run `GET /api/audit/verify` and confirm 0 tampered files
- [ ] No records deleted within their 7-year retention window
- [ ] Paper receipts scanned within 2 months + 7 business days of receipt
- [ ] This 事務処理規程 is on file with your accountant

## インボイス制度 Checklist

- [ ] All receipts with a 登録番号 have been NTA-validated in the app
- [ ] Any receipt from an unregistered vendor is noted in MoneyForward with the correct reduced deduction rate
- [ ] 80% rule applies to unregistered vendors through Sep 30, 2026
- [ ] 50% rule applies Oct 1, 2026 through Sep 30, 2029
- [ ] All qualified invoices retained for 7 years

## NTA Invoice Lookup API

Public API — no authentication required:
```
GET https://web-api.invoice-kohyo.nta.go.jp/1/num?id=T{13digits}&type=21
```
Response field `res.registrations[0].process` = `"01"` means registered and active.

Full API docs: https://www.invoice-kohyo.nta.go.jp/web-api/index.html
