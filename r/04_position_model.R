# Logistic regression of click on position, random vs normal searches. Needs: ggplot2
suppressMessages(library(ggplot2))
d <- read.csv("r/model_input.csv")
d$log_pos <- log(d$position); d$log_price <- log(d$price_usd); d$log_bw <- log1p(d$srch_booking_window)
d$random <- factor(d$random_bool, labels = c("Normal ranking", "Random order"))

# M1: position effect, and how much weaker/stronger it is under random order
m1 <- glm(click_bool ~ log_pos * random + prop_starrating + prop_review_score + prop_location_score1 +
          log_price + promotion_flag, data = d, family = binomial)
# M2: random searches only (clean causal read), position effect varies with lead time and stay length
r <- subset(d, random_bool == 1)
m2 <- glm(click_bool ~ log_pos * log_bw + log_pos * srch_length_of_stay + prop_starrating +
          prop_review_score + log_price + promotion_flag, data = r, family = binomial)

or_table <- function(m) { ci <- confint.default(m)   # Wald CIs: fast on large n
  round(data.frame(odds_ratio = exp(coef(m)), lo95 = exp(ci[, 1]), hi95 = exp(ci[, 2])), 3) }
dir.create("reports", showWarnings = FALSE)
sink("reports/r_model_summary.txt"); cat("== M1: all searches ==\n"); print(or_table(m1))
cat("\n== M2: random searches only ==\n"); print(or_table(m2))
cat("\nReading: exp(coef of log_pos) = multiplicative change in click ODDS when position doubles... (per e-fold; use 2^b for doubling)\n"); sink()

g <- expand.grid(position = 1:40, random = levels(d$random), stringsAsFactors = FALSE)
g$log_pos <- log(g$position); g$random_f <- factor(g$random, levels = levels(d$random))
for (v in c("prop_starrating", "prop_review_score", "prop_location_score1", "promotion_flag")) g[[v]] <- median(d[[v]], na.rm = TRUE)
g$log_price <- median(d$log_price); g$random <- g$random_f
g$p <- predict(m1, g, type = "response")
p <- ggplot(g, aes(position, p, colour = random)) + geom_line(linewidth = 1.2) +
  scale_colour_manual(values = c("Normal ranking" = "#1f3a5f", "Random order" = "#e07a1f"), name = NULL) +
  scale_y_continuous(labels = scales::percent) +
  labs(title = "Position alone moves click odds, even with no quality signal", x = "Position", y = "Predicted click probability",
       subtitle = "Median hotel, logistic model M1") + theme_minimal(base_size = 12) + theme(legend.position = "top")
ggsave("reports/figures/04_r_position_effect.png", p, width = 8, height = 4.5, dpi = 160)
