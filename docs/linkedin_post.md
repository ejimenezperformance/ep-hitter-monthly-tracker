# LinkedIn post (attach figures/persistence_by_metric.png and figures/batspeed_to_next_xwoba.png)

Which monthly flags on a hitter are real?

I tested every MLB hitter in 2026 (183,849 PA, Statcast). Question: when a hitter's month moves away from his season line, how much of that change shows up again the next month?

▪ Bat speed: 44% carries over (95% CI 0.31–0.57). CONFIRMED.
▪ wOBA, xwOBA, K%: no measurable carry-over. A hot or cold month is just more data.
▪ Chase% and Barrel%: about 15%. Real, but small.
▪ Reacting fully to last month made forecasts 18–21% worse.

Then I tested the next step: does a slower-bat month come with a worse next month? No. Not in xwOBA, Barrel% or exit velocity (NOT CONFIRMED, rules set before the run).

Takeaway: a bat-speed drop is a real physical signal for the strength, medical and hitting staff. It is not a production forecast. And don't change a role over one month of wOBA.

Method note: comparing the month with the prior months only creates fake persistence. On a synthetic league with no real changes it gave 0.37. I used a pooled baseline and kept that warning test in the repo.

Also built: an Excel tracker for all 30 teams (pick a team and a hitter, 21 metrics by month, live formulas).

Repo: github.com/ejimenezperformance/ep-hitter-monthly-tracker

—

¿Qué alertas mensuales de un bateador son reales?

Probé a todos los bateadores de MLB en 2026 (183,849 PA, Statcast). Pregunta: cuando el mes de un bateador se aleja de su línea de la temporada, ¿cuánto de ese cambio aparece otra vez el mes siguiente?

▪ Bat speed: se mantiene el 44% (IC 95% 0.31–0.57). CONFIRMED.
▪ wOBA, xwOBA, K%: no se mantiene nada medible. Un mes caliente o frío es solo más datos.
▪ Chase% y Barrel%: alrededor del 15%. Real, pero pequeño.
▪ Reaccionar por completo al último mes empeoró el pronóstico entre 18% y 21%.

Después probé el siguiente paso: ¿un mes con el bate más lento viene con un peor mes siguiente? No. Ni en xwOBA, ni en Barrel%, ni en velocidad de salida (NOT CONFIRMED, reglas fijadas antes de correr los datos).

Conclusión: una caída de bat speed es una señal física real para el cuerpo de fuerza, médico y de bateo. No es un pronóstico de producción. Y no hay que cambiar un rol por un mes de wOBA.

Nota de método: comparar el mes solo con los meses anteriores crea persistencia falsa. En una liga sintética sin cambios reales dio 0.37. Usé una base acumulada y dejé esa prueba de advertencia en el repo.

También construí un Excel para los 30 equipos (eliges equipo y bateador, 21 métricas por mes, fórmulas vivas).

Repo: github.com/ejimenezperformance/ep-hitter-monthly-tracker

#MLB #Baseball #SportsAnalytics #Statcast #StrengthAndConditioning

---

# GitHub "About" (≤350 characters)

Which monthly hitter flags are real? All MLB hitters 2026 (Statcast): 44% of a monthly bat-speed change carries into the next month, but it did not predict next-month production; wOBA, xwOBA and K% carry nothing measurable. Plus an Excel tracker for all 30 teams.

Website: https://ejimenezperformance.github.io
Topics: mlb, baseball, statcast, sports-analytics, bat-tracking, python, excel, strength-and-conditioning
