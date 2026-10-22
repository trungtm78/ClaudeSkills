# Compliance Checklists for UAT

Checklist test theo các framework compliance phổ biến. Đọc khi feature liên quan tới regulation cụ thể.

## ⭐ Cập nhật quy định 2025-2026 (ảnh hưởng trực tiếp UAT)

### EDPB Guidelines on Pseudonymisation (01/2025) — TEST DATA
- **Masked production data VẪN LÀ personal data** (pseudonymisation ≠ anonymisation — bản gốc còn khôi phục được) → môi trường test giữ masked-prod **vẫn trong scope GDPR** (Art. 32/5/25).
- Dùng production data không mask ở dev/test = vi phạm Art. 5(1)(a). Môi trường test thường có 3-5× số người truy cập so với production — rủi ro nhân lên.
- **Kết luận cho UAT: synthetic-by-construction là mặc định.** Chỉ dùng masked-prod khi cần độ chân thực thống kê, và khi đó flag `data_classification: personal-data` + ghi nhận môi trường trong scope.

### FDA CSA final guidance (24/09/2025, rev 02/2026) + GAMP 5 2nd Edition
- Risk-based assurance thay thế exhaustive documentation: tập trung effort vào chức năng ảnh hưởng an toàn/chất lượng, "critical thinking" thay giấy tờ máy móc.
- **Evidence hợp lệ giờ gồm cả scripted, UNSCRIPTED (exploratory/ad-hoc), và vendor-supplied evidence** → exploratory charter session là bằng chứng UAT hợp lệ kể cả trong regulated, miễn charter-scoped + có evidence.
- Hàm ý: artifact UAT gọn nhưng chất lượng cao + traceable > tài liệu đồ sộ.

### OWASP MASVS / MASTG — MOBILE security (khi platform mobile)
- MASVS = chuẩn yêu cầu bảo mật mobile app; MASTG = hướng dẫn kiểm thử tương ứng. Nhóm TC MOBILE-SEC neo vào đây:
  - Không lộ secrets/PII trong logcat/console
  - Screenshot-blocking trên màn hình nhạy cảm (app switcher blank)
  - Cert pinning / TLS đúng
  - Deep-link không bypass auth
  - Clipboard hygiene với dữ liệu nhạy cảm
  - Lưu trữ cục bộ (keychain/keystore) thay plaintext

## A. GDPR (General Data Protection Regulation - EU)

Áp dụng khi app có user EU hoặc xử lý PII (Personally Identifiable Information).

### Quyền của user (Data Subject Rights)

| Quyền | Test case bắt buộc |
|-------|---------------------|
| **Right to Access** (Art 15) | User download được toàn bộ data của mình (JSON/CSV) trong ≤30 ngày |
| **Right to Rectification** (Art 16) | User sửa được thông tin cá nhân |
| **Right to Erasure** (Art 17) | User xóa account → data bị xóa hoàn toàn (hoặc anonymize) |
| **Right to Portability** (Art 20) | Download data ở format machine-readable |
| **Right to Object** (Art 21) | Opt-out marketing email |
| **Right to Restrict Processing** (Art 18) | Pause processing nhưng giữ data |

### Consent Management

| Test | Expected |
|------|----------|
| Checkbox consent KHÔNG pre-checked | Default unchecked |
| Consent cho từng mục đích riêng | Marketing, analytics, third-party share separate |
| User withdraw consent dễ | Trong settings, không phải email |
| Cookie banner có lựa chọn rõ | "Accept", "Reject", "Customize" |
| Cookie banner reject = thực sự không track | Verify Network tab không có analytics |
| Bằng chứng consent được log | Timestamp, IP, version policy |

### Data Breach

- App có cơ chế detect breach
- Notification trong 72h (Art 33)
- Audit log không bị tamper

### Cross-border transfer

- Data EU không transfer sang nước không có adequacy decision
- SCC (Standard Contractual Clauses) cho transfer

### Privacy by Design (Art 25)

| Test | Expected |
|------|----------|
| Default privacy settings | Most private |
| Minimization | Chỉ collect data cần thiết |
| Pseudonymization | PII không hiển thị nguyên ở admin panel |
| Retention | Data tự xóa sau N năm |

### TC mẫu GDPR

```markdown
| TC-ID | TC-COMP-GDPR-001 |
|-------|-------------------|
| **Loại** | AUDIT |
| **Độ ưu tiên** | P0 |
| **Compliance** | GDPR Art 17 - Right to Erasure |
| **Tiêu đề** | User xóa account → data PII bị xóa/anonymize trong 30 ngày |
| **Điều kiện tiên quyết** | User "alice" có: profile, orders, comments, messages |
| **Các bước kiểm thử** | 1. Login alice<br>2. Settings → Delete Account → confirm<br>3. Verify ngay: tài khoản logout, không login lại được<br>4. Sau 30 ngày, query DB qua admin:<br>   - bảng users: email = 'deleted-{id}@anonymized.local', name = 'DELETED USER'<br>   - bảng orders: vẫn còn cho audit nhưng user_id = NULL hoặc anonymized<br>   - bảng comments: bị xóa hoặc anonymize<br>   - backup: bị xóa khỏi backup mới |
| **Kết quả mong đợi** | 1. UI: Confirm dialog "Đây là hành động không hoàn tác"<br>2. API: POST /api/users/me/delete → 202 Accepted<br>3. Email gửi: "Yêu cầu xóa đã nhận, hoàn tất trong 30 ngày"<br>4. Audit log: "user_deletion_requested" với user_id, timestamp, IP<br>5. Sau 30 ngày: PII bị anonymize, không có cách nào identify user<br>6. Order data giữ cho legal (7 năm) nhưng đã anonymized |
| **Severity nếu fail** | Critical (S1) — GDPR fine up to 4% global revenue |
```

---

## B. PCI-DSS (Payment Card Industry Data Security Standard)

Áp dụng khi app xử lý credit card.

### 12 yêu cầu chính

| Req | Test |
|-----|------|
| 1. Firewall | Không direct database access từ internet |
| 2. Default password | Không có admin/admin còn dùng được |
| 3. Cardholder data | KHÔNG lưu CVV, KHÔNG lưu full PAN (mask: ****1234) |
| 4. Encrypt transmission | HTTPS bắt buộc, TLS ≥1.2 |
| 5. Antivirus | (server-side, không UAT) |
| 6. Secure systems | Patch up to date |
| 7. Access by need-to-know | Role-based access tới payment data |
| 8. Identify access | Unique user ID, không shared account |
| 9. Physical access | (out of UAT) |
| 10. Logging | Log mọi access tới cardholder data |
| 11. Test security | Penetration test định kỳ |
| 12. Policy | Documented |

### Test bắt buộc

```markdown
| TC-ID | TC-COMP-PCI-001 |
|-------|-------------------|
| **Loại** | SECURITY |
| **Compliance** | PCI-DSS Req 3.4 - Mask PAN |
| **Tiêu đề** | Credit card number được mask khi hiển thị, không lưu CVV |
| **Test Steps** | 1. User checkout, nhập card 4111111111111111, CVV 123<br>2. Submit thanh toán thành công<br>3. Vào trang Order detail xem method<br>4. Query DB qua admin |
| **Expected** | 1. UI Order detail hiển thị: "VISA ****1111"<br>2. KHÔNG có nơi nào hiển thị full PAN<br>3. DB bảng payments:<br>   - card_last4 = "1111" ✓<br>   - card_token = "tok_xxx" (từ Stripe/payment gateway) ✓<br>   - card_full_pan: KHÔNG TỒN TẠI hoặc encrypted<br>   - cvv: KHÔNG TỒN TẠI ⚠️ vi phạm PCI nếu có<br>4. Log không chứa PAN hay CVV<br>5. Email confirmation chỉ hiển thị ****1111 |
| **Severity nếu fail** | Critical — PCI fine + mất quyền nhận payment |
```

---

## C. SOX (Sarbanes-Oxley Act - US Public Companies)

Áp dụng khi feature liên quan financial reporting.

### Test bắt buộc

| Area | Test |
|------|------|
| **Audit trail** | Mọi thay đổi financial data có log: who, what, when, why |
| **Segregation of duties** | Người create transaction ≠ người approve |
| **Change management** | Approval flow cho thay đổi quan trọng |
| **Access control** | Role-based, principle of least privilege |
| **Data integrity** | Không thể edit/delete log audit |
| **Backup & recovery** | Test recovery process |

---

## D. HIPAA (Health Insurance Portability and Accountability Act - US Healthcare)

Áp dụng khi app xử lý PHI (Protected Health Information).

### Test bắt buộc

| Area | Test |
|------|------|
| **Encryption at rest** | PHI trong DB encrypted |
| **Encryption in transit** | HTTPS bắt buộc, không expose PHI qua HTTP |
| **Access logging** | Mọi truy cập PHI có log |
| **Minimum necessary** | User chỉ thấy PHI cần cho task |
| **De-identification** | PHI được de-identify khi export báo cáo |
| **Breach notification** | Cơ chế detect và notify breach |
| **BAA** | Tích hợp với 3rd party có BAA agreement |

---

## E. ISO 27001 (Information Security Management)

Test cho compliance ISO 27001:

| Area | Test |
|------|------|
| **Access control** (A.9) | Role-based, periodic review |
| **Cryptography** (A.10) | Key management, TLS |
| **Operations security** (A.12) | Logging, monitoring, patch |
| **Communications security** (A.13) | Network segmentation, encryption |
| **System acquisition/maintenance** (A.14) | Secure SDLC |
| **Supplier relationships** (A.15) | 3rd party assessment |
| **Incident management** (A.16) | Incident response plan |
| **Business continuity** (A.17) | Backup, DR test |
| **Compliance** (A.18) | Regular audit |

---

## F. WCAG 2.2 Level AA (Accessibility)

Pháp lý: ADA (US), EAA (EU 2025), AODA (Canada Ontario).

Xem chi tiết: `references/accessibility-wcag.md`

---

## G. CCPA (California Consumer Privacy Act)

Áp dụng nếu có user California (US).

Tương tự GDPR nhưng narrower:

| Right | Test |
|-------|------|
| Right to Know | Hiển thị data đang collect |
| Right to Delete | Xóa account + data |
| Right to Opt-Out | "Do Not Sell My Info" link |
| Right to Non-Discrimination | Không phạt user opt-out |

---

## H. Vietnam Cybersecurity Law (LAT 2018, Decree 53/2022)

Áp dụng nếu app cho user Việt Nam.

### Test bắt buộc

| Area | Test |
|------|------|
| **Data localization** | Data của user VN lưu tại VN (cho domains cụ thể) |
| **User verification** | KYC cho service có rủi ro cao |
| **Content moderation** | Cơ chế report + takedown |
| **Cooperation with authority** | Audit log accessible cho authority khi yêu cầu (theo quy định) |
| **PII protection** | Theo Nghị định 13/2023/NĐ-CP về bảo vệ dữ liệu cá nhân |

### Nghị định 13/2023 (PDPL Vietnam)

| Test | Expected |
|------|----------|
| Consent rõ ràng | Trước khi xử lý PII |
| Quyền user | Access, rectify, delete, restrict |
| Data breach notification | Cơ quan có thẩm quyền trong 72h |
| DPO appointed | Nếu xử lý sensitive PII |
| Cross-border transfer | Theo quy định Bộ Công an |

---

## I. Industry-specific

### Banking (SBV - Việt Nam)

- Thông tư 35/2018/TT-NHNN về an toàn hệ thống thông tin
- Lưu log transaction ≥10 năm
- Audit định kỳ
- KYC theo Thông tư 35/2017/TT-NHNN

### E-commerce (Việt Nam)

- Nghị định 52/2013/NĐ-CP về thương mại điện tử
- Niêm yết thông tin người bán
- Bảo vệ người tiêu dùng

### Education

- FERPA (US) cho data sinh viên
- COPPA (US) cho user <13 tuổi

---

## Quick reference: Compliance ảnh hưởng test cases như thế nào?

Khi feature liên quan compliance, **thêm các TC sau vào bộ UAT chuẩn**:

| Compliance | TC bổ sung |
|------------|------------|
| GDPR | +5-8 TC AUDIT (consent, erasure, access, log) |
| PCI-DSS | +3-5 TC SECURITY (mask, no CVV, encryption) |
| SOX | +3-5 TC AUDIT (segregation, audit trail) |
| HIPAA | +5-8 TC SECURITY (encryption, access log, de-identify) |
| Vietnam PDPL | +3-5 TC AUDIT (consent, retention, breach) |
| WCAG AA | +5 TC A11Y (đã có trong skill base) |

**Quy tắc bắt buộc:** Khi user nhắc tới feature payment, healthcare, banking, education, hoặc app có user EU/US/VN — HỎI user về compliance scope ngay trong Bước 1 (Recap).
