import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
import warnings
warnings.filterwarnings('ignore')

df = pd.read_csv('/home/claude/meesho_orders.csv')

# ── color palette ──────────────────────────────────────────────────────────────
CORAL   = '#E8593C'
TEAL    = '#1D9E75'
PURPLE  = '#7F77DD'
AMBER   = '#EF9F27'
GRAY    = '#888780'
BG      = '#FAFAF8'
DARK    = '#2C2C2A'

plt.rcParams.update({
    'font.family': 'DejaVu Sans',
    'axes.spines.top': False,
    'axes.spines.right': False,
    'axes.facecolor': BG,
    'figure.facecolor': 'white',
    'axes.edgecolor': '#D3D1C7',
    'axes.labelcolor': DARK,
    'xtick.color': GRAY,
    'ytick.color': GRAY,
    'text.color': DARK,
})

# ══════════════════════════════════════════════════════════════════════════════
# FIGURE 1 — 4-panel EDA
# ══════════════════════════════════════════════════════════════════════════════
fig = plt.figure(figsize=(16, 10), facecolor='white')
gs  = GridSpec(2, 2, figure=fig, hspace=0.38, wspace=0.35)

# 1a: Return rate by category
ax1 = fig.add_subplot(gs[0, 0])
cat_ret = (df.groupby('product_category')['return_flag'].mean() * 100).sort_values(ascending=False)
colors_cat = [CORAL if v > 50 else AMBER if v > 40 else TEAL for v in cat_ret.values]
bars = ax1.barh(cat_ret.index, cat_ret.values, color=colors_cat, height=0.6, edgecolor='none')
for bar, val in zip(bars, cat_ret.values):
    ax1.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2,
             f'{val:.1f}%', va='center', fontsize=10, fontweight='500', color=DARK)
ax1.set_xlabel('Return Rate (%)')
ax1.set_title('Return Rate by Category', fontsize=13, fontweight='500', pad=10)
ax1.set_xlim(0, 75)
ax1.tick_params(axis='y', labelsize=10)
ax1.set_facecolor(BG)

# 1b: COD vs Prepaid
ax2 = fig.add_subplot(gs[0, 1])
pay_ret = df.groupby('payment_type')['return_flag'].mean() * 100
x = np.arange(2)
bar_colors = [CORAL, TEAL]
bars2 = ax2.bar(x, pay_ret.values, color=bar_colors, width=0.45, edgecolor='none')
for bar, val in zip(bars2, pay_ret.values):
    ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
             f'{val:.1f}%', ha='center', fontsize=12, fontweight='500', color=DARK)
ax2.set_xticks(x)
ax2.set_xticklabels(['COD', 'Prepaid'], fontsize=11)
ax2.set_ylabel('Return Rate (%)')
ax2.set_title('COD vs Prepaid Return Rate', fontsize=13, fontweight='500', pad=10)
ax2.set_ylim(0, 70)
lift = ((pay_ret['COD'] - pay_ret['Prepaid']) / pay_ret['Prepaid']) * 100
ax2.annotate(f'{lift:.0f}% higher for COD', xy=(0.5, 50), ha='center', fontsize=9,
             color=CORAL, style='italic')
ax2.set_facecolor(BG)

# 1c: Seller rating vs returns
ax3 = fig.add_subplot(gs[1, 0])
df['seller_bin'] = pd.cut(df['seller_rating'], bins=[0,2,3,4,5], labels=['1-2★','2-3★','3-4★','4-5★'])
sr_ret = df.groupby('seller_bin')['return_flag'].mean() * 100
sr_colors = [CORAL, AMBER, AMBER, TEAL]
bars3 = ax3.bar(sr_ret.index.astype(str), sr_ret.values, color=sr_colors, width=0.5, edgecolor='none')
for bar, val in zip(bars3, sr_ret.values):
    ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
             f'{val:.1f}%', ha='center', fontsize=10, fontweight='500', color=DARK)
ax3.set_xlabel('Seller Rating')
ax3.set_ylabel('Return Rate (%)')
ax3.set_title('Seller Rating vs Return Rate', fontsize=13, fontweight='500', pad=10)
ax3.set_ylim(0, 80)
ax3.set_facecolor(BG)

# 1d: Delivery delay vs returns
ax4 = fig.add_subplot(gs[1, 1])
df['delay_bin'] = pd.cut(df['delivery_days'], bins=[0,2,4,6,10],
                          labels=['1-2 days','3-4 days','5-6 days','7+ days'])
del_ret = df.groupby('delay_bin')['return_flag'].mean() * 100
del_colors = [TEAL, TEAL, AMBER, CORAL]
bars4 = ax4.bar(del_ret.index.astype(str), del_ret.values, color=del_colors, width=0.5, edgecolor='none')
for bar, val in zip(bars4, del_ret.values):
    ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
             f'{val:.1f}%', ha='center', fontsize=10, fontweight='500', color=DARK)
ax4.set_xlabel('Delivery Time')
ax4.set_ylabel('Return Rate (%)')
ax4.set_title('Delivery Days vs Return Rate', fontsize=13, fontweight='500', pad=10)
ax4.set_ylim(0, 80)
ax4.set_facecolor(BG)

fig.suptitle('Meesho RRIS — Exploratory Data Analysis', fontsize=16, fontweight='500', y=0.98, color=DARK)
plt.savefig('/home/claude/eda_analysis.png', dpi=150, bbox_inches='tight', facecolor='white')
plt.close()
print("EDA figure saved.")

# ══════════════════════════════════════════════════════════════════════════════
# RISK SCORE ENGINE
# ══════════════════════════════════════════════════════════════════════════════
def compute_rrs(row):
    score = 0
    if row['payment_type'] == 'COD': score += 25
    if row['seller_rating'] < 3:     score += 30
    elif row['seller_rating'] < 4:   score += 15
    if row['delivery_days'] > 7:     score += 20
    elif row['delivery_days'] > 5:   score += 10
    if row['user_past_returns'] >= 3: score += 20
    elif row['user_past_returns'] >= 1: score += 10
    if row['product_category'] == 'Fashion': score += 15
    return min(score, 100)

df['rrs'] = df.apply(compute_rrs, axis=1)
df['risk_tier'] = pd.cut(df['rrs'], bins=[-1, 25, 50, 75, 100],
                          labels=['Low', 'Medium', 'High', 'Very High'])

# FIGURE 2 — Risk Score Distribution + Tier Analysis
fig, axes = plt.subplots(1, 2, figsize=(14, 5), facecolor='white')

# 2a: RRS Distribution by Return Status
ax = axes[0]
ret_scores  = df[df['return_flag']==1]['rrs']
nret_scores = df[df['return_flag']==0]['rrs']
bins = range(0, 105, 5)
ax.hist(nret_scores, bins=bins, alpha=0.65, color=TEAL,  label='No Return', edgecolor='none')
ax.hist(ret_scores,  bins=bins, alpha=0.65, color=CORAL, label='Returned',  edgecolor='none')
ax.set_xlabel('Return Risk Score (RRS)')
ax.set_ylabel('Order Count')
ax.set_title('RRS Distribution by Return Outcome', fontsize=13, fontweight='500', pad=10)
ax.legend(fontsize=10)
ax.set_facecolor(BG)

# 2b: Return rate by Risk Tier
ax2 = axes[1]
tier_ret   = df.groupby('risk_tier')['return_flag'].mean() * 100
tier_count = df.groupby('risk_tier').size()
tier_cols  = [TEAL, AMBER, '#D85A30', CORAL]
bars = ax2.bar(tier_ret.index.astype(str), tier_ret.values, color=tier_cols, width=0.5, edgecolor='none')
for bar, val, cnt in zip(bars, tier_ret.values, tier_count):
    ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.8,
             f'{val:.1f}%\nn={cnt}', ha='center', fontsize=9, fontweight='500', color=DARK)
ax2.set_xlabel('Risk Tier')
ax2.set_ylabel('Return Rate (%)')
ax2.set_title('Return Rate by Risk Tier', fontsize=13, fontweight='500', pad=10)
ax2.set_ylim(0, 95)
ax2.set_facecolor(BG)

fig.suptitle('Return Risk Score (RRS) Analysis', fontsize=15, fontweight='500', y=1.01, color=DARK)
plt.tight_layout()
plt.savefig('/home/claude/risk_score_analysis.png', dpi=150, bbox_inches='tight', facecolor='white')
plt.close()
print("Risk score figure saved.")

# ══════════════════════════════════════════════════════════════════════════════
# LOGISTIC REGRESSION MODEL
# ══════════════════════════════════════════════════════════════════════════════
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score, confusion_matrix
from sklearn.preprocessing import StandardScaler

features_df = pd.get_dummies(df[['payment_type','product_category']], drop_first=True)
numeric_features = df[['price','seller_rating','delivery_days','user_past_returns']]
X = pd.concat([numeric_features.reset_index(drop=True), features_df.reset_index(drop=True)], axis=1)
y = df['return_flag']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
scaler = StandardScaler()
X_train_s = scaler.fit_transform(X_train)
X_test_s  = scaler.transform(X_test)

model = LogisticRegression(max_iter=1000, random_state=42)
model.fit(X_train_s, y_train)
y_pred = model.predict(X_test_s)
y_proba = model.predict_proba(X_test_s)[:,1]

auc = roc_auc_score(y_test, y_proba)
report = classification_report(y_test, y_pred)
print(f"\nModel AUC-ROC: {auc:.3f}")
print(report)

# Feature importance
coef_df = pd.DataFrame({'feature': X.columns, 'coef': model.coef_[0]})
coef_df = coef_df.reindex(coef_df['coef'].abs().sort_values(ascending=False).index)

# FIGURE 3 — Feature Importance
fig, ax = plt.subplots(figsize=(10, 6), facecolor='white')
colors_fi = [CORAL if c > 0 else TEAL for c in coef_df['coef'].values]
bars = ax.barh(coef_df['feature'], coef_df['coef'], color=colors_fi, height=0.6, edgecolor='none')
ax.axvline(0, color=GRAY, linewidth=0.8, linestyle='--')
for bar, val in zip(bars, coef_df['coef'].values):
    x_pos = val + (0.02 if val > 0 else -0.02)
    ax.text(x_pos, bar.get_y() + bar.get_height()/2,
            f'{val:.3f}', va='center', ha='left' if val > 0 else 'right',
            fontsize=9, color=DARK)
ax.set_xlabel('Logistic Regression Coefficient')
ax.set_title(f'Feature Importance for Return Prediction  (AUC = {auc:.3f})', fontsize=13, fontweight='500', pad=10)
pos_patch = mpatches.Patch(color=CORAL, label='Increases return risk')
neg_patch = mpatches.Patch(color=TEAL,  label='Decreases return risk')
ax.legend(handles=[pos_patch, neg_patch], fontsize=10)
ax.set_facecolor(BG)
plt.tight_layout()
plt.savefig('/home/claude/feature_importance.png', dpi=150, bbox_inches='tight', facecolor='white')
plt.close()
print("Feature importance saved.")

# ══════════════════════════════════════════════════════════════════════════════
# MONTHLY TREND
# ══════════════════════════════════════════════════════════════════════════════
df['order_date'] = pd.to_datetime(df['order_date'])
df['month'] = df['order_date'].dt.to_period('M')
monthly = df.groupby('month').agg(
    orders=('order_id','count'),
    returns=('return_flag','sum'),
    return_rate=('return_flag','mean')
).reset_index()
monthly['month_str'] = monthly['month'].astype(str)

fig, ax1 = plt.subplots(figsize=(14, 5), facecolor='white')
ax2 = ax1.twinx()
ax1.bar(monthly['month_str'], monthly['orders'], color=PURPLE, alpha=0.5, edgecolor='none', label='Total Orders')
ax2.plot(monthly['month_str'], monthly['return_rate']*100, color=CORAL, linewidth=2.5,
         marker='o', markersize=5, label='Return Rate %')
ax1.set_xlabel('Month')
ax1.set_ylabel('Order Volume', color=PURPLE)
ax2.set_ylabel('Return Rate (%)', color=CORAL)
ax1.tick_params(axis='x', rotation=45)
ax1.set_facecolor(BG)
ax1.set_title('Monthly Order Volume & Return Rate Trend', fontsize=13, fontweight='500', pad=10)
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=10)
fig.set_facecolor('white')
plt.tight_layout()
plt.savefig('/home/claude/monthly_trend.png', dpi=150, bbox_inches='tight', facecolor='white')
plt.close()
print("Monthly trend saved.")

# Save enriched dataset
df.to_csv('/home/claude/meesho_orders_enriched.csv', index=False)
print("\nAll analysis complete!")
print(f"Dataset shape: {df.shape}")

# Print key insights
print("\n━━━ KEY INSIGHTS ━━━")
print(f"Fashion return rate:       {df[df['product_category']=='Fashion']['return_flag'].mean():.1%}")
print(f"COD return rate:           {df[df['payment_type']=='COD']['return_flag'].mean():.1%}")
print(f"Prepaid return rate:       {df[df['payment_type']=='Prepaid']['return_flag'].mean():.1%}")
print(f"Low seller (<3★) returns:  {df[df['seller_rating']<3]['return_flag'].mean():.1%}")
print(f"High seller (4+★) returns: {df[df['seller_rating']>=4]['return_flag'].mean():.1%}")
print(f"7+ day delivery returns:   {df[df['delivery_days']>7]['return_flag'].mean():.1%}")
print(f"Very High RRS returns:     {df[df['risk_tier']=='Very High']['return_flag'].mean():.1%}")
print(f"Low RRS returns:           {df[df['risk_tier']=='Low']['return_flag'].mean():.1%}")
