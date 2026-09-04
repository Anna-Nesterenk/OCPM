# OCPM Lens — Object-Centric Process Investigation Environment

Інтерактивний Streamlit-застосунок для дослідження бізнес-процесу
Supply-to-Customer методом Object-Centric Process Mining: один процес,
шість точок входу (Supplier, Product, Batch, Customer, Product Category,
Supply Channel), можливість переходити між пов'язаними об'єктами і
знаходити наскрізні інсайти.

Побудовано за результатами дослідження датасету
`OCPM_Supply_to_Customer_Dataset_v1`.

## Запуск

```bash
pip install -r requirements.txt
streamlit run app.py
```

Дані вже лежать у папці `data/` поруч з `app.py`. Якщо потрібно
використати інший зріз того самого датасету — просто замініть CSV-файли
в `data/` (перелік обов'язкових файлів — у `data_loader.REQUIRED_FILES`).

## Структура проєкту

```
app.py                 # тонкий вхідний файл: завантажує дані, малює сайдбар
                        # з глобальними фільтрами, реєструє сторінки (st.navigation)
data/                   # CSV-файли датасету
data_loader.py          # читання CSV + побудова наскрізної таблиці batch_full
data_model.py           # типи об'єктів, кольори, Filters, session-state дефолти
metrics.py              # спільні агрегації/форматування (KPI, цикли)
ocpm_graph.py           # NetworkX-граф об'єктів + Plotly-рендер
analytics/              # по одному модулю на бізнес-об'єкт (product/supplier/
                        # batch/customer/category/channel) — KPI + пов'язані таблиці
insights.py             # Insight Engine: детектори п'яти категорій інсайтів,
                        # що рахуються наживо з поточного зрізу даних
visualizations.py       # спільні Plotly-графіки (матриці, box plot, sankey, journey)
navigation.py           # session_state, глобальні фільтри, drill-down між сторінками
ui.py                   # спільні UI-компоненти (KPI-плитки, insight-картки, таблиці)
pages/                  # 9 сторінок застосунку (Overview, Explore, Product,
                        # Supplier, Batch, Supply Channel, Customer, Insights,
                        # Methodology)
```

## Ключова ідея

> Почавши дослідження з одного бізнес-об'єкта, можна перейти до інших
> пов'язаних об'єктів і побачити повний бізнес-контекст проблеми чи
> можливості — те, що складно чи неможливо побачити в традиційній
> process-centric моделі з одним Case ID.

Сторінка **Methodology** пояснює це на конкретних прикладах із самого
датасету (зокрема — чому Purchase Order як Case ID не дає жодної
варіативності процесу, а Batch — дає).
