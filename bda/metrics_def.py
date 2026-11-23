"""Metric registry: one place that defines every number the pipeline reports.

direction: "lower" = smaller is better, "higher" = bigger is better, "info" = no judgement.
camera:    "back", "side" or "any".
version:   bump when the formula changes; compare.py refuses to compare different versions.
"""

METRICS = {
    # --- legs / ready position (back camera)
    "neutral_high_share":   dict(ru="Высоко между ударами, % времени", unit="%", direction="lower", camera="back", version=1),
    "neutral_narrow_share": dict(ru="Стопы уже плеч между ударами, % времени", unit="%", direction="lower", camera="back", version=1),
    "neutral_leg_rel":      dict(ru="Высота стойки между ударами, % от ходьбы", unit="%", direction="lower", camera="back", version=1),
    "high_share_after_break": dict(ru="Высоко между ударами после перерыва, %", unit="%", direction="lower", camera="back", version=1),
    # --- overheads (back camera)
    "oh_count":             dict(ru="Ударов сверху", unit="", direction="info", camera="back", version=1),
    "oh_turned_share":      dict(ru="Удары сверху с разворотом, %", unit="%", direction="higher", camera="back", version=1),
    "oh_square_share":      dict(ru="Удары сверху грудью к сетке, %", unit="%", direction="lower", camera="back", version=1),
    "oh_leftarm_up_share":  dict(ru="Левая рука вверху перед ударом, %", unit="%", direction="higher", camera="back", version=1),
    "oh_reach_median":      dict(ru="Высота кисти над головой, длин корпуса", unit="", direction="higher", camera="back", version=1),
    "oh_jump_share":        dict(ru="Удары сверху в прыжке, %", unit="%", direction="info", camera="back", version=1),
    # --- lunges (back camera)
    "lunge_per_min":        dict(ru="Выпадов в минуту розыгрыша", unit="/мин", direction="info", camera="back", version=1),
    "lunge_lean_share":     dict(ru="Выпады с завалом корпуса >25°, %", unit="%", direction="lower", camera="back", version=1),
    "lunge_left_share":     dict(ru="Выпады влево, % от всех", unit="%", direction="info", camera="back", version=1),
    # --- court position (back camera)
    "pos_left_share":       dict(ru="Время на левой половине, %", unit="%", direction="info", camera="back", version=1),
    "pos_right_share":      dict(ru="Время на правой половине, %", unit="%", direction="info", camera="back", version=1),
    # --- side camera (v1, experimental: 45° view from the net post)
    "side_neutral_knee_median": dict(ru="Угол колена между ударами (сбоку), °", unit="°", direction="lower", camera="side", version=1),
    "side_neutral_straight_share": dict(ru="Колени почти прямые (>160°) между ударами, %", unit="%", direction="lower", camera="side", version=1),
    "side_lunge_knee_min_median": dict(ru="Угол колена в выпаде (сбоку), °", unit="°", direction="info", camera="side", version=1),
    "side_lunge_trunk_fwd_median": dict(ru="Наклон корпуса вперёд в выпаде (сбоку), °", unit="°", direction="lower", camera="side", version=1),
    # --- volume
    "rally_count":          dict(ru="Розыгрышей", unit="", direction="info", camera="any", version=1),
    "rally_minutes":        dict(ru="Чистое время розыгрышей, мин", unit="мин", direction="info", camera="any", version=1),
}
