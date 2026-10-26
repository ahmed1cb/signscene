# شرح مشروع SignScene

> **ملاحظة عن مصدر المعلومات:** كل ما في هذا الملف مستنتج من الملفات المرسلة فقط. الاسم "SignScene" مأخوذ من عنوان النافذة ومن أسماء المتغيرات. بعض الملفات التي تستدعيها الواجهة لم تُرسل (انظر قسم "ملفات غير مرسلة")، لذا ما يخصها استنتاج وليس مؤكدًا.

---

## 1. فكرة المشروع

تطبيق سطح مكتب (Python + PySide6) يساعد على التواصل بلغة الإشارة عبر مكالمة بين مستخدمين:

1. الكاميرا تلتقط يدي المستخدم.
2. MediaPipe يستخرج 21 نقطة لكل يد.
3. يُحوَّل شكل اليد وحركتها إلى كلمة بمطابقة قوالب سجّلها المستخدم بنفسه (Teachable).
4. الكلمات تتجمع في جملة، وتُرسَل تلقائيًا بعد 4 ثوانٍ من غياب اليد.
5. الجملة تُرسل نصًا أو صورة رموز (Pictograms) عبر WebSocket، وتُنطق صوتيًا عند الطرف الآخر.

---

## 2. هيكل الملفات

```
core/
├── message.py          نموذج الرسالة
├── settings.py         إعدادات الصوت
├── session.py          حفظ جلسة تسجيل الدخول
├── api_client.py       REST: تسجيل/دخول/me
├── realtime.py         WebSocket: المكالمات والمحتوى
├── speaker.py          النطق الصوتي (TTS)
├── scene.py            توليد صورة رموز من ARASAAC
├── scene_api.py        استدعاء خادم لمعالجة الجملة (غير مستخدم حاليًا)
├── camera.py           خيط الكاميرا + التتبع + التعرف
└── asl/
    ├── features.py     حالات الأصابع
    ├── gesture_types.py هياكل البيانات + الـ buffer
    ├── templates.py    القوالب + مطابقة DTW
    ├── gesture_engine.py منسّق التعرف لكل إطار
    └── decoder.py      بناء الجملة
ui/
├── styles.py           ألوان وأنماط QSS
└── main_window.py      النافذة الرئيسية والتنقل بين الشاشات
```

(مسارات المجلدات استنتجتها من أسطر `import`.) ملفا `__init__.py` فارغان، ووظيفتهما جعل المجلدين حزمتين.

---

## 3. مسار البيانات الكامل

```
الكاميرا (OpenCV)
   │  إطار BGR → قلب مرآة → RGB
   ▼
MediaPipe HandLandmarker (يدان كحد أقصى)
   │  21 نقطة + تسمية Left/Right
   ▼
GestureEngine.update()
   │  FeatureExtractor → حالات الأصابع
   │  SignBuffer      → نافذة آخر 2.5 ثانية
   │  TemplateStore.match() كل 3 إطارات → DTW
   ▼
كلمة (word, confidence)  + تبريد 1.2 ثانية
   ▼
SentenceBuilder.add_word() → sentence_changed
   │  4 ثوانٍ بلا يد
   ▼
sentence_ready(text)
   ├─► RealtimeClient.send_text / send_scene  → الطرف الآخر
   ├─► SceneWorker.generate(text)             → صورة رموز
   └─► Speaker.say(Message("txt", text))      → نطق
```

الجزء الأخير (من `sentence_ready` فصاعدًا) استنتاج: الربط يتم في `HomeScreen` الذي لم يُرسل.

---

## 4. وحدة التعرف على الإشارات (`core/asl/`)

### 4.1 `features.py`: من النقاط إلى حالات

**فهارس MediaPipe المستخدمة:** المعصم 0، والإبهام 1/2/4، والسبابة 5/6/8، والوسطى 9/10/12، والبنصر 13/14/16، والخنصر 17/18/20.

**التعدادات:** `FingerState` و`ThumbState`، كلاهما: `CURLED=0` و`HALF=1` و`EXTENDED=2`.

**`HandFeatures`** يحمل حالة الأصابع الخمسة.

**الدوال الهندسية:** `_sub` و`_dot` و`_norm` و`_angle_between` (زاوية بالدرجات، وترجع 180 إن كان أحد المتجهين شبه صفري).

**`_finger_state`** يقيس زاوية الانحناء عند المفصل PIP بين المتجهين (MCP←PIP) و(TIP←PIP):

| الزاوية | الحالة |
| ------- | ------ |
| ≥ 150°  | ممدود  |
| ≥ 105°  | نصف    |
| غير ذلك | منحنٍ  |

**الإبهام:** الزاوية بين (CMC→MCP) و(MCP→TIP) بعتبتين: 150° و115°.

> تنبيه: الوصف في أعلى الملف يقول "world landmarks (metric)" لكن الكود يقرأ `x, y, z` من النقاط التي يمررها `GestureEngine`. وفي `camera.py` تأتي من `result.hand_landmarks` وهي إحداثيات مطبّعة، وليست world landmarks. الزوايا مع ذلك تبقى مفيدة، لكن الإحداثيات المطبّعة تتأثر بنسبة أبعاد الصورة (استنتاج).

### 4.2 `gesture_types.py`: هياكل البيانات

- **`HandFrame`:** يد واحدة في إطار واحد: `handedness` و`features` و`points_xy` (21 نقطة) و`palm_normal` (متجه عمودي على الراحة) و`hand_size`.
  - خاصية `palm_center`: متوسط المعصم وقواعد الأصابع الأربعة (5, 9, 13, 17).
- **`SignFrame`:** إطار زمني: `t_ms` وقاموس `hands` مفاتيحه "Left"/"Right".
- **`SignBuffer`:** `deque` بحد أقصى 150 إطارًا، ويحذف ما هو أقدم من 2.5 ثانية عند كل إضافة.

### 4.3 `gesture_engine.py`: المنسّق

**ثوابت:** `WORD_COOLDOWN_MS=1200` و`TEMPLATE_EVERY=3` (المطابقة كل 3 إطارات توفيرًا للمعالج).

**`GestureResult`:** نتيجة كل إطار: `word` و`word_confidence` و`recorded_word` و`recording` و`record_remaining_ms`.

**`update(ts_ms, hands)`** لكل إطار:

1. يبني `HandFrame` لكل يد ويدمجها في `SignFrame`، ثم يضيفه للـ buffer.
2. **وضع التسجيل** (إن كان `_record_word` غير فارغ): يجمع الإطارات ويعيد `recording=True` والزمن المتبقي. عند انتهاء المدة يحفظ العينة ويعيد `recorded_word`، ثم **يعود فورًا** دون مطابقة.
3. **التبريد:** إن لم ينتهِ تبريد آخر كلمة يعود فارغًا.
4. **المطابقة:** إن وُجدت يد وكان رقم الإطار من مضاعفات 3، يأخذ إطارات آخر **2000 مللي ثانية** ويستدعي `templates.match`. عند النجاح: يُحدَّد `word`، ويبدأ تبريد 1.2 ثانية، ويُفرَّغ الـ buffer حتى لا تتكرر الكلمة.

**`_build_hand_frame`:** يحتفظ بـ `FeatureExtractor` منفصل لكل يد، ويحسب `hand_size = |Δy| + |Δx|` بين المعصم وقاعدة الوسطى، ويحسب `palm_normal`.

**`_palm_normal`:** حاصل الضرب الاتجاهي لمتجهين: (المعصم→قاعدة السبابة) و(المعصم→قاعدة الخنصر)، ثم تطبيع.

**`_active_hand`:** يفضّل "Right"، وإلا يأخذ أول يد.

### 4.4 `templates.py`: القوالب والمطابقة

**الفكرة:** المستخدم "يعلّم" التطبيق كلمة بتنفيذ الإشارة 2 ثانية. تُخزَّن العينة، وعند الاستخدام تُقارَن حركة اليد الحالية بكل العينات.

**`frame_vector`**: متجه من **18 رقمًا** لكل إطار:

| الفهارس | المحتوى                                              |
| ------- | ---------------------------------------------------- |
| 0–4     | حالات الأصابع الخمسة (0 / 0.5 / 1) لليد الأساسية     |
| 5–7     | `palm_normal`                                        |
| 8–9     | `palm_center` (x, y)                                 |
| 10      | علامة وجود اليد الثانية (1.0 أو 0)                   |
| 11–12   | موضع اليد الثانية نسبةً للأولى، مقسومًا على حجم اليد |
| 13–17   | حالات أصابع اليد الثانية                             |

إن لم توجد يد ثانية فالفهارس 10–17 أصفار.

**مراحل المعالجة:**

1. `_normalize_positions`: يطرح موقع أول إطار من (8, 9)، فلا يهم مكان تنفيذ الإشارة في الصورة.
2. `_resample`: استيفاء خطي لتوحيد الطول إلى **30 إطارًا**.
3. `dtw_distance`: خوارزمية DTW بتكلفة إقليدية بين الإطارات، والنتيجة مقسومة على `max(n, m)`.

**`TemplateStore`:**

- `add_sample`: يتطلب **5 إطارات** على الأقل فيها يد، ثم يضيف العينة ويحفظ.
- `clear_word` و`sample_count`.
- `match`: لكل كلمة يأخذ أقل مسافة بين عيناتها، ثم يرتب. شروط القبول:
  - أقل مسافة ≤ `MATCH_THRESHOLD = 4.5`.
  - إن وُجدت كلمة ثانية: يجب أن تكون المسافة ≤ 0.85 × مسافة الثانية (هامش تمييز).
  - الثقة = `1 - المسافة/4.5` مقيّدة بين 0 و1.
- التخزين في `gestures.json` ضمن مجلد AppConfig الخاص بـ Qt.

> تنبيه: تعليق `_normalize_positions` يذكر "scale by palm size" لكن الكود يزيح الموقع فقط ولا يقسم على حجم اليد.

**تكلفة الحساب (استنتاج):** DTW بحجم 30×30 لكل عينة × عدد العينات، كل 3 إطارات. مقبول لعدد قليل من الكلمات، وقد يثقل مع قوالب كثيرة.

### 4.5 `decoder.py`: بناء الجملة

`SentenceBuilder`:

- `add_word`: ينظف المسافات ويضيف الكلمة، ثم يستدعي `on_sentence_changed`.
- `tick(ts_ms, has_hand)`: إن وُجدت يد يصفّر العداد. وإن غابت يبدأ العد، وبعد **4000 مللي ثانية** وبوجود نص، يرسل `on_sentence_ready(text)` ويفرّغ الجملة.
- `clear_sentence`: يفرّغ الجملة والعداد.

---

## 5. الكاميرا (`core/camera.py`)

`CameraWorker(QThread)` يشغّل الحلقة في خيط مستقل.

**الإشارات (Signals):**

| الإشارة                         | المعنى                |
| ------------------------------- | --------------------- |
| `frame_ready(ndarray)`          | إطار RGB للعرض        |
| `status_changed(str)`           | رسالة الحالة          |
| `sentence_changed(str)`         | الجملة قيد البناء     |
| `sentence_ready(str)`           | جملة جاهزة للإرسال    |
| `gesture_detected(word, conf)`  | كلمة مكتشفة           |
| `gesture_recorded(word, total)` | انتهى تسجيل عينة      |
| `record_progress(ms)`           | الزمن المتبقي للتسجيل |
| `fps_changed(float)`            | معدل الإطارات         |
| `stopped()`                     | توقف الخيط            |

**الطلبات الآمنة بين الخيوط:** `stop()` و`request_clear()` و`request_record(word)`، وهي أعلام تُقرأ داخل الحلقة.

**حلقة `run`:**

1. يفتح الكاميرا 0، وإن فشل يرسل "Camera unavailable" ويتوقف.
2. ينشئ `HandLandmarker` (وضع VIDEO، يدان) من `assets/models/hand_landmarker.task`، وإن فشل يحرر الكاميرا ويتوقف.
3. لكل إطار: قراءة ← قلب أفقي (مرآة) ← تحويل إلى RGB ← اكتشاف مع طابع زمني متزايد دومًا (`ts_ms` يُجبر على الزيادة) ← بناء قائمة `hands` برسم الهيكل ← تنفيذ الطلبات المعلّقة ← `engine.update` ← إرسال الإشارات ← `builder.tick` ← رسم HUD ← إرسال الإطار.
4. FPS: عدد الإطارات في آخر ثانيتين ÷ الزمن المنقضي، ويُرسَل كل 0.5 ثانية.
5. `finally`: يحرر الكاميرا ويغلق الـ landmarker ويرسل `stopped`.

**`_apply_requests`:** عند طلب المسح يفرّغ الجملة والـ buffer. وعند طلب التسجيل (ولا تسجيل جارٍ) يبدأ تسجيل `RECORD_MS = 2000`.

**الرسم:** `_draw_hud` مستطيل صغير باسم الكلمة المكتشفة، و`_draw_landmarks` يرسم الخطوط والنقاط.

> تنبيهات:
>
> - **ألوان BGR على صورة RGB:** الثوابت مكتوبة بصيغة BGR (التعليق `#FFB703` برتقالي)، لكن الرسم يتم على مصفوفة RGB، فسيظهر اللون أزرق بدل البرتقالي. الحل: تبديل ترتيب القيم في الثوابت.
> - **تسمية اليد:** إن أعطى MediaPipe التسمية نفسها ليدين، فسيستبدل `frame.hands[handedness]` إحداهما بالأخرى (استنتاج من بنية القاموس).
> - `self.status_changed. emit` فيه مسافة بعد النقطة؛ صحيح نحويًا لكن غير منسق.

---

## 6. الشبكة والحساب

### 6.1 `api_client.py` (REST)

- `BASE_URL = "http://127.0.0.1:8080"` **ثابت في الكود**.
- `_post` و`_get` بمهلة 5 ثوانٍ، وأي خطأ HTTP ≥ 400 أو استثناء `requests` يتحول إلى `AuthError` برسالة الخادم (`error`) إن وُجدت.
- `register(full_name, com_id, password)` ← `/auth/register`.
- `login(com_id, password)` ← `/auth/login`، وإن عاد توكن يحفظه عبر `session.save`.
- `me(token)` ← `/auth/me`.
- معرّف المستخدم اسمه `com_id`.

### 6.2 `session.py`

- يحفظ `{"token", "user"}` في `session.json` ضمن AppConfig، وينشئ المجلد إن لزم.
- `chmod 600` لتقييد الوصول (لا يفيد على Windows).
- `load()` يعيد `None` عند غياب الملف أو تلفه. `clear()` يحذفه بأمان.

### 6.3 `realtime.py` (WebSocket)

`RealtimeClient(QObject)` يتصل بـ `ws://127.0.0.1:8080/ws` (قابل للتغيير بالمتغير `SIGNSCENE_WS_URL`).

**الإشارات:** `ready` و`ringing` و`incoming` و`accepted` و`rejected` و`ended` و`content` و`error(code, message)` و`connection_changed(bool)`.

**الأوامر:**

| الدالة                                     | رسالة الخادم                                            |
| ------------------------------------------ | ------------------------------------------------------- |
| `start_call(com_id)`                       | `call.start` إلى معرّف                                  |
| `accept_call` / `reject_call` / `end_call` | `call.accept` / `call.reject` / `call.end` بـ `call_id` |
| `send_text(call_id, text)`                 | `content.send` بنوع `text`                              |
| `send_scene(call_id, scene)`               | `content.send` بنوع `scene`                             |

**الدورة:**

1. `connect(token)` يفتح الاتصال.
2. عند `connected` يرسل `{"type": "auth", "token": ...}`.
3. عند وصول `ready` يصبح الحال جاهزًا.
4. `_send` يعيد `False` إن لم يكن الاتصال قائمًا.

**إعادة الاتصال:** تأخير أسي `1s × 2^المحاولة` بحد أقصى 15 ثانية. **لا إعادة اتصال** عند رمز الإغلاق **4001** (الحساب فُتح من جهاز آخر) أو **4003** (توثيق فاشل)، بل يُرسل `error` مناسب.

> تنبيهات:
>
> - الدالة `connect` تحجب اسم `QObject.connect` الموروث (استنتاج). الإشارات تعمل عبر `signal.connect` فلا مشكلة عمليًا، لكن الاسم مربك.
> - الاتصال غير مشفّر (`http`/`ws`)؛ مناسب للتطوير المحلي فقط. في الإنتاج استخدم `https`/`wss`.

---

## 7. الصور التوضيحية

### 7.1 `scene.py` (المستخدم)

`SceneWorker(QThread)` يحوّل جملة إلى صورة رموز من **ARASAAC**.

**الإشارات:** `scene_ready(sentence, data_uri)` و`scene_failed(sentence, error)` و`status_changed` و`model_loaded`.

**الخطوات:**

1. `generate(sentence)` يضع الجملة في طابور.
2. `_words`: يستخرج الكلمات (أحرف يونيكود فقط، بلا أرقام)، ويحذف `STOPWORDS` الإنجليزية والتكرار.
3. `_search_id`: يبحث عن رمز الكلمة عبر `api.arasaac.org` (نتيجة 404 = لا رمز)، ويخزن النتيجة في ذاكرة مؤقتة داخل الذاكرة.
4. `_fetch_image`: ينزّل `500px` ويحفظها في `~/.cache/signscene/arasaac`.
5. يتوقف عند **6 رموز** (`MAX_PICTOS`).
6. `_compose`: شبكة بـ 3 أعمدة كحد أقصى، حجم المربع 512 لرمز واحد وإلا 256، على خلفية بيضاء.
7. يحفظ JPEG بجودة 88 ويرسله كـ `data:image/jpeg;base64,...`.

**الترخيص:** CC BY-NC-SA؛ مطلوب ذكر المصدر، والاستخدام غير تجاري فقط (حسب تعليق الكود).

**اللغة:** المتغير `SIGNSCENE_ARASAAC_LANG` (الافتراضي `en`). قائمة الكلمات المحذوفة إنجليزية فقط، فعند تغيير اللغة يلزم تعديلها.

### 7.2 `scene_api.py` (غير مستخدم حاليًا)

`process_sentence` يرسل الجملة إلى `/scene/process` ويتوقع `prompt` و`negative_prompt` و`defaults`. يبدو من مسار قديم لتوليد صور بالذكاء الاصطناعي (استنتاج). يحتوي `print(data)` زائدًا للتنقيح.

---

## 8. الصوت والإعدادات

### 8.1 `settings.py`

الافتراضيات: `voice_id=None` و`voice_name=None` و`rate=100` و`volume=1.0`. `load()` يقرأ `settings.json` ويدمج المفاتيح المعروفة فقط، ويعود للافتراضي عند أي خطأ.

### 8.2 `speaker.py`

محرك `pyttsx3` **في خيط مستقل** بطابور مهام، لأن النطق يحجب التنفيذ.

- `_worker`: ينشئ المحرك ويضبط السرعة والمستوى ويخزّن الأصوات المتاحة ثم يعلن الجاهزية (`_ready`). بعدها ينتظر المهام: `("say", نص)` أو `(خاصية, قيمة)`.
- `_start`: يشغّل الخيط إن لم يكن حيًا (محمي بقفل).
- `list_voices()`: ينتظر `_ready` ثم يعيد (id, name).
- `_resolve_voice_id`: يبحث بالمعرّف أولًا ثم بالاسم.
- `apply_saved()`: يعيد تحميل الإعدادات ويطبقها.
- `Speaker.say(msg)`: ينطق فقط الرسائل من نوع `txt`.

> تنبيه (استنتاج): إن فشل `pyttsx3.init()` داخل `_worker` فلن تُضبط `_ready` أبدًا، وسيتجمد `list_voices()` للأبد.

### 8.3 `message.py`

`Message(type, content, mine=True)`: نوع الرسالة (`txt` وغيره) والمحتوى والملكية (لي/للطرف الآخر، تُستخدم لاختيار شكل الفقاعة).

---

## 9. الواجهة (`ui/`)

### 9.1 `styles.py`

يعرّف لوحة الألوان وسلسلة QSS واحدة `APP_STYLESHEET`.

**الألوان:**

| الاسم             | القيمة                | الاستخدام                  |
| ----------------- | --------------------- | -------------------------- |
| ACCENT            | `#FFB703`             | لون التمييز (برتقالي-ذهبي) |
| BG                | `#0B1330`             | الخلفية                    |
| PANEL / PANEL_ALT | `#111D40` / `#182A55` | اللوحات والحقول            |
| BORDER            | `#263A6B`             | الحدود                     |
| TEXT / TEXT_MUTED | `#F4F7FF` / `#9CABCF` | النصوص                     |
| ERROR / SUCCESS   | `#FF6B6B` / `#4DD0D4` | الخطأ / النجاح             |

**المحددات حسب `objectName`:**

- `#Card` بطاقات.
- `#TitleBar` و`#Brand` و`#WindowButton` و`#WindowCloseButton` (الأخير يتحول للأحمر عند التمرير).
- `#Title` و`#Subtitle` عناوين.
- حقول `QLineEdit` مع حالات `invalid="true"` و`valid="true"` بخاصية ديناميكية.
- `QPushButton` (الأصفر) و`#LinkButton` و`#GhostButton` و`#DangerButton`.
- `#CameraVideo` و`#CameraHud` و`#ComposingLabel` (الجملة الجارية) و`#GestureLabel`.
- `#SceneSplitter` و`#MainMessagesSplitter` (المقابض شفافة وتظهر عند التمرير).
- `#ScenePreview` معاينة الصورة.
- `#IncomingCallBar` و`#IncomingCallLabel` شريط المكالمة الواردة.
- `#MessageScroll` و`#BubbleMine` و`#BubbleTheirs` فقاعات الرسائل.
- `#Hint` و`#StatusDot` و`#ErrorLabel` و`#SuccessLabel` و`QCheckBox` و`#TogglePassword`.

> ملاحظة: بعض كتل QSS داخل الـ f-string مُزاحة بمسافات زائدة؛ لا تؤثر على العمل.

### 9.2 `main_window.py`

`MainWindow(QWidget)`: النافذة الرئيسية.

**نافذة بلا إطار (Frameless):**

- `FramelessWindowHint` مع شريط عنوان مخصص `TitleBar` (استُورد من `ui.widgets.titlebar`).
- الحد الأدنى للحجم 1100×720، والعنوان "SignScene".

**تغيير الحجم بالسحب (`_ResizeHandle`):**

- 8 مقابض شفافة (4 حواف + 4 زوايا) بسماكة `RESIZE_MARGIN = 6` بكسل.
- عند الضغط تستدعي `startSystemResize(edges)` ليتولى نظام التشغيل تغيير الحجم، مع مؤشر مناسب لكل مقبض.
- `_layout_handles` يعيد وضعها عند تغيير الحجم، و`_update_handle_visibility` يخفيها عند التكبير أو ملء الشاشة.
- `changeEvent` يزامن زر التكبير في شريط العنوان (`titlebar.sync_maximize()`).

**الشاشات (`QStackedWidget`):**

| الشاشة           | الدور                                 |
| ---------------- | ------------------------------------- |
| `LoginScreen`    | تسجيل الدخول                          |
| `RegisterScreen` | إنشاء حساب                            |
| `HomeScreen`     | الشاشة الرئيسية (الكاميرا والمكالمات) |

**التنقل:**

- `_enter_home(user)`: يضبط اسم المستخدم ومعرّفه، يقرأ التوكن المحفوظ، يبدأ الاتصال الفوري `start_realtime(token)`، ثم يعرض الشاشة الرئيسية.
- `show_login()` (يُستدعى عند الخروج أيضًا): يوقف الاتصال الفوري، **يمسح الجلسة**، ويفرّغ حقول الدخول وحالة المكالمة.
- `show_register()`: يفرّغ نموذج التسجيل ويعرضه.
- `_go_to_login_after_register(user)`: يملأ `com_id` بأحرف كبيرة، ويفرّغ كلمة المرور، ويعرض "Account created. Please sign in."
- `closeEvent`: يوقف الكاميرا والاتصال الفوري قبل الإغلاق.

> ملاحظات:
>
> - في `closeEvent` لا يُوقَف `SceneWorker` هنا؛ ربما يتم داخل `HomeScreen` (غير مرسل).
> - المتغير `screen = Qt.CursorShape` اسمه مضلل (يخص المؤشرات لا الشاشة).

---

## 10. ملفات غير مرسلة (يستدعيها `main_window.py`)

- `ui/screens/home_screen.py` (`HomeScreen`) وواجهاته المستخدمة: `set_user`, `start_realtime`, `shutdown_realtime`, `shutdown_camera`, `peer_edit`, `call_status`.
- `ui/screens/login_screen.py` (`LoginScreen`): `reset`, `com_id_edit`, `password.edit`, `clear_messages`, `show_info`.
- `ui/screens/register_screen.py` (`RegisterScreen`): `reset`.
- `ui/widgets/titlebar.py` (`TitleBar`): `sync_maximize`.
- ملف الدخول الرئيسي (`main.py`) الذي ينشئ `QApplication` ويطبّق `APP_STYLESHEET`.
- الخادم (Node.js حسب تعليق `api_client.py`) ومنفذه 8080.
- النموذج `assets/models/hand_landmarker.task`.

---

## 11. ملخص الملاحظات والمشكلات المحتملة

| #   | الملف                           | الملاحظة                                               | النوع             |
| --- | ------------------------------- | ------------------------------------------------------ | ----------------- |
| 1   | `camera.py`                     | ثوابت BGR تُرسم على صورة RGB فتنقلب الألوان            | خطأ مؤكد من الكود |
| 2   | `templates.py`                  | التعليق يذكر التحجيم بحجم الراحة والكود لا يفعله       | تعليق غير مطابق   |
| 3   | `features.py`                   | التعليق يذكر world landmarks والمستخدم إحداثيات مطبّعة | تعليق غير مطابق   |
| 4   | `api_client.py`                 | عنوان الخادم ثابت، بينما غيره يقرأه من متغيرات البيئة  | تناسق             |
| 5   | `api_client.py` / `realtime.py` | `http` و`ws` بلا تشفير                                 | أمان (للإنتاج)    |
| 6   | `session.py`                    | التوكن نصٌّ عادي في ملف (`chmod` لا يفيد على Windows)  | أمان              |
| 7   | `scene_api.py`                  | `print(data)` زائد، والملف غير مستخدم                  | نظافة             |
| 8   | `scene.py`                      | قائمة الكلمات المحذوفة إنجليزية فقط                    | قيد               |
| 9   | `speaker.py`                    | احتمال تجمّد `list_voices()` إن فشل `init()`           | استنتاج           |
| 10  | `realtime.py`                   | الدالة `connect` تحجب اسم `QObject.connect`            | استنتاج           |
| 11  | `camera.py`                     | تكرار تسمية اليد قد يستبدل إحدى اليدين                 | استنتاج           |

---

## 12. ملحق: المتغيرات البيئية

| المتغير                                        | الافتراضي                | الاستخدام          |
| ---------------------------------------------- | ------------------------ | ------------------ |
| `SIGNSCENE_WS_URL`                             | `ws://127.0.0.1:8080/ws` | عنوان WebSocket    |
| `SIGNSCENE_API_BASE` / `SIGNSCENE_BACKEND_URL` | `http://127.0.0.1:8080`  | `scene_api.py` فقط |
| `SIGNSCENE_ARASAAC_LANG`                       | `en`                     | لغة بحث الرموز     |
