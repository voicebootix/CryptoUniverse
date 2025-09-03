import {
  TradingReport,
  ReportFormat,
  ReportGenerationOptions,
} from "@/types/reports";
import { formatCurrency, formatPercentage, downloadFile } from "@/lib/utils";

class ReportService {
  private formatDataForCSV(data: TradingReport): string {
    const rows = [
      // Header row
      ["Report Generated", data.timestamp],
      ["Total Balance", formatCurrency(data.total_balance)],
      ["24h P&L", formatCurrency(data.total_pnl_24h)],
      ["24h Volume", formatCurrency(data.total_volume_24h)],
      ["Win Rate", formatPercentage(data.overall_win_rate)],
      ["Active Positions", data.active_positions.toString()],
      [],
      // Exchange section
      ["Exchange Performance"],
      ["Exchange", "Balance", "24h P&L", "Trades", "Win Rate", "Status"],
      ...data.exchanges.map((ex) => [
        ex.name,
        formatCurrency(ex.balance),
        formatCurrency(ex.pnl_24h),
        ex.trades_24h.toString(),
        formatPercentage(ex.win_rate),
        ex.connection_status,
      ]),
      [],
      // Arbitrage section
      ["Active Arbitrage Opportunities"],
      [
        "Pair",
        "Buy Exchange",
        "Buy Price",
        "Sell Exchange",
        "Sell Price",
        "Profit",
        "Risk",
      ],
      ...data.arbitrage_opportunities.map((opp) => [
        opp.symbol,
        opp.buy_exchange,
        formatCurrency(opp.buy_price),
        opp.sell_exchange,
        formatCurrency(opp.sell_price),
        `${opp.profit_bps} bps`,
        opp.execution_complexity,
      ]),
    ];

    return rows.map((row) => row.join(",")).join("\\n");
  }

  private generateHTML(data: TradingReport): string {
    return `
<!DOCTYPE html>
<html>
<head>
    <title>Exchange Hub Trading Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { text-align: center; color: #4A90E2; margin-bottom: 30px; }
        .section { margin-bottom: 30px; }
        .section h2 { color: #333; border-bottom: 2px solid #4A90E2; padding-bottom: 5px; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #4A90E2; color: white; }
        tr:nth-child(even) { background-color: #f2f2f2; }
        .overview-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; }
        .metric-card { background: #f9f9f9; padding: 15px; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Exchange Hub Trading Report</h1>
        <p>Generated on: ${new Date(data.timestamp).toLocaleString()}</p>
    </div>

    <div class="section">
        <h2>Overview</h2>
        <div class="overview-grid">
            <div class="metric-card">
                <strong>Total Balance:</strong> ${formatCurrency(
                  data.total_balance
                )}
            </div>
            <div class="metric-card">
                <strong>24h P&L:</strong> ${formatCurrency(data.total_pnl_24h)}
            </div>
            <div class="metric-card">
                <strong>24h Volume:</strong> ${formatCurrency(
                  data.total_volume_24h
                )}
            </div>
            <div class="metric-card">
                <strong>Win Rate:</strong> ${formatPercentage(
                  data.overall_win_rate
                )}
            </div>
        </div>
    </div>

    <div class="section">
        <h2>Exchange Performance</h2>
        <table>
            <thead>
                <tr>
                    <th>Exchange</th>
                    <th>Balance</th>
                    <th>24h P&L</th>
                    <th>Trades</th>
                    <th>Win Rate</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                ${data.exchanges
                  .map(
                    (ex) => `
                    <tr>
                        <td>${ex.name}</td>
                        <td>${formatCurrency(ex.balance)}</td>
                        <td>${formatCurrency(ex.pnl_24h)}</td>
                        <td>${ex.trades_24h}</td>
                        <td>${formatPercentage(ex.win_rate)}</td>
                        <td>${ex.connection_status}</td>
                    </tr>
                `
                  )
                  .join("")}
            </tbody>
        </table>
    </div>

    <div class="section">
        <h2>Arbitrage Opportunities</h2>
        <table>
            <thead>
                <tr>
                    <th>Pair</th>
                    <th>Buy Exchange</th>
                    <th>Buy Price</th>
                    <th>Sell Exchange</th>
                    <th>Sell Price</th>
                    <th>Profit</th>
                    <th>Risk</th>
                </tr>
            </thead>
            <tbody>
                ${data.arbitrage_opportunities
                  .map(
                    (opp) => `
                    <tr>
                        <td>${opp.symbol}</td>
                        <td>${opp.buy_exchange}</td>
                        <td>${formatCurrency(opp.buy_price)}</td>
                        <td>${opp.sell_exchange}</td>
                        <td>${formatCurrency(opp.sell_price)}</td>
                        <td>${opp.profit_bps} bps</td>
                        <td>${opp.execution_complexity}</td>
                    </tr>
                `
                  )
                  .join("")}
            </tbody>
        </table>
    </div>
</body>
</html>
    `;
  }

  public async generateReport(
    data: TradingReport,
    options: ReportGenerationOptions
  ): Promise<void> {
    const timestamp = new Date().toISOString().split("T")[0];
    const filename = `exchange-hub-report-${timestamp}`;

    try {
      switch (options.format) {
        case "csv": {
          const csvContent = this.formatDataForCSV(data);
          downloadFile(csvContent, `${filename}.csv`, "text/csv");
          break;
        }

        case "json": {
          const jsonContent = JSON.stringify(data, null, 2);
          downloadFile(jsonContent, `${filename}.json`, "application/json");
          break;
        }

        case "pdf": {
          const htmlContent = this.generateHTML(data);
          downloadFile(htmlContent, `${filename}.html`, "text/html");
          break;
        }

        default:
          throw new Error(`Unsupported format: ${options.format}`);
      }
    } catch (error) {
      console.error("Failed to generate report:", error);
      throw error;
    }
  }
}

export const reportService = new ReportService();
