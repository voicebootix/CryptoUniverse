import {
  TradingReport,
  ReportFormat,
  ReportGenerationOptions,
} from "@/types/reports";
import { formatCurrency, formatPercentage, downloadFile } from "@/lib/utils";

class ReportService {
  private escapeHTML(value: unknown): string {
    const s = String(value ?? "");
    return s
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  private escapeCSVField(field: string): string {
    // Convert to string and handle null/undefined
    const str = String(field || "");

    // Check if field needs escaping (contains comma, quote, or newline)
    if (
      str.includes(",") ||
      str.includes('"') ||
      str.includes("\n") ||
      str.includes("\r")
    ) {
      // Replace any double-quotes with two double-quotes and wrap in quotes
      return `"${str.replace(/"/g, '""')}"`;
    }

    return str;
  }

  private sanitizeData(
    data: TradingReport,
    options: ReportGenerationOptions
  ): TradingReport {
    if (options.include_sensitive_data) {
      return data;
    }

    // Create sanitized copy
    const sanitized: TradingReport = {
      ...data,
      exchanges: data.exchanges.map((ex) => ({
        ...ex,
        balance: 0, // Redact balance
        pnl_24h: 0, // Redact P&L
      })),
      total_balance: 0, // Redact total balance
      total_pnl_24h: 0, // Redact total P&L
      total_volume_24h: 0, // Redact volume
    };

    return sanitized;
  }

  private formatDataForCSV(
    data: TradingReport,
    options: ReportGenerationOptions
  ): string {
    const sanitizedData = this.sanitizeData(data, options);
    const rows: string[][] = [];

    // Always include timestamp
    rows.push(["Report Generated", sanitizedData.timestamp]);
    rows.push(["Time Range", options.time_range]);
    rows.push([]);

    // Overview section
    if (options.sections.includes("overview")) {
      rows.push(["Overview"]);
      rows.push(["Total Balance", formatCurrency(sanitizedData.total_balance)]);
      rows.push(["24h P&L", formatCurrency(sanitizedData.total_pnl_24h)]);
      rows.push(["24h Volume", formatCurrency(sanitizedData.total_volume_24h)]);
      rows.push([
        "Win Rate",
        formatPercentage(sanitizedData.overall_win_rate),
      ]);
      rows.push([
        "Active Positions",
        sanitizedData.active_positions.toString(),
      ]);
      rows.push([]);
    }

    // Exchange section
    if (options.sections.includes("exchanges")) {
      rows.push(["Exchange Performance"]);
      rows.push([
        "Exchange",
        "Balance",
        "24h P&L",
        "Trades",
        "Win Rate",
        "Status",
      ]);
      rows.push(
        ...sanitizedData.exchanges.map((ex) => [
          ex.name,
          formatCurrency(ex.balance),
          formatCurrency(ex.pnl_24h),
          ex.trades_24h.toString(),
          formatPercentage(ex.win_rate),
          ex.connection_status,
        ])
      );
      rows.push([]);
    }

    // Arbitrage section
    if (options.sections.includes("arbitrage")) {
      rows.push(["Active Arbitrage Opportunities"]);
      rows.push([
        "Pair",
        "Buy Exchange",
        "Buy Price",
        "Sell Exchange",
        "Sell Price",
        "Profit",
        "Risk",
      ]);
      rows.push(
        ...sanitizedData.arbitrage_opportunities.map((opp) => [
          opp.pair,
          opp.buyExchange,
          formatCurrency(opp.buyPrice),
          opp.sellExchange,
          formatCurrency(opp.sellPrice),
          `${opp.spreadPct.toFixed(2)} %`,
          opp.risk,
        ])
      );
      rows.push([]);
    }

    // Performance section
    if (options.sections.includes("performance")) {
      rows.push(["Performance Metrics"]);
      rows.push(["Exchange", "Trades", "Win Rate", "Avg Profit", "Volume"]);
      rows.push(
        ...sanitizedData.performance_metrics.map((metric) => [
          metric.exchange_name,
          metric.trades.toString(),
          formatPercentage(metric.win_rate),
          formatCurrency(metric.avg_profit),
          formatCurrency(metric.volume),
        ])
      );
      rows.push([]);
    }

    return rows
      .map((row) => row.map((field) => this.escapeCSVField(field)).join(","))
      .join("\r\n");
  }

  private generateHTML(
    data: TradingReport,
    options: ReportGenerationOptions
  ): string {
    const sanitizedData = this.sanitizeData(data, options);

    let sectionsHTML = "";

    // Overview section
    if (options.sections.includes("overview")) {
      sectionsHTML += `
    <div class="section">
        <h2>Overview</h2>
        <div class="overview-grid">
            <div class="metric-card">
                <strong>Total Balance:</strong> ${formatCurrency(
                  sanitizedData.total_balance
                )}
            </div>
            <div class="metric-card">
                <strong>24h P&L:</strong> ${formatCurrency(
                  sanitizedData.total_pnl_24h
                )}
            </div>
            <div class="metric-card">
                <strong>24h Volume:</strong> ${formatCurrency(
                  sanitizedData.total_volume_24h
                )}
            </div>
            <div class="metric-card">
                <strong>Win Rate:</strong> ${formatPercentage(
                  sanitizedData.overall_win_rate / 100
                )}
            </div>
        </div>
    </div>`;
    }

    // Exchange section
    if (options.sections.includes("exchanges")) {
      sectionsHTML += `
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
                ${sanitizedData.exchanges
                  .map(
                    (ex) => `
                    <tr>
                        <td>${this.escapeHTML(ex.name)}</td>
                        <td>${formatCurrency(ex.balance)}</td>
                        <td>${formatCurrency(ex.pnl_24h)}</td>
                        <td>${ex.trades_24h}</td>
                        <td>${formatPercentage(ex.win_rate)}</td>
                        <td>${this.escapeHTML(ex.connection_status)}</td>
                    </tr>
                `
                  )
                  .join("")}
            </tbody>
        </table>
    </div>`;
    }

    // Arbitrage section
    if (options.sections.includes("arbitrage")) {
      sectionsHTML += `
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
                ${sanitizedData.arbitrage_opportunities
                  .map(
                    (opp) => `
                    <tr>
                        <td>${this.escapeHTML(opp.pair)}</td>
                        <td>${this.escapeHTML(opp.buyExchange)}</td>
                        <td>${formatCurrency(opp.buyPrice)}</td>
                        <td>${this.escapeHTML(opp.sellExchange)}</td>
                        <td>${formatCurrency(opp.sellPrice)}</td>
                        <td>${opp.spreadPct.toFixed(2)}%</td>
                        <td>${this.escapeHTML(opp.risk)}</td>
                    </tr>
                `
                  )
                  .join("")}
            </tbody>
        </table>
    </div>`;
    }

    // Performance section
    if (options.sections.includes("performance")) {
      sectionsHTML += `
    <div class="section">
        <h2>Performance Metrics</h2>
        <table>
            <thead>
                <tr>
                    <th>Exchange</th>
                    <th>Trades</th>
                    <th>Win Rate</th>
                    <th>Avg Profit</th>
                    <th>Volume</th>
                </tr>
            </thead>
            <tbody>
                ${sanitizedData.performance_metrics
                  .map(
                    (metric) => `
                    <tr>
                        <td>${this.escapeHTML(metric.exchange_name)}</td>
                        <td>${metric.trades}</td>
                        <td>${formatPercentage(metric.win_rate)}</td>
                        <td>${formatCurrency(metric.avg_profit)}</td>
                        <td>${formatCurrency(metric.volume)}</td>
                    </tr>
                `
                  )
                  .join("")}
            </tbody>
        </table>
    </div>`;
    }

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
        <p>Generated on: ${this.escapeHTML(
          new Date(sanitizedData.timestamp).toLocaleString()
        )}</p>
        <p>Time Range: ${this.escapeHTML(options.time_range)}</p>
        <p>Data Level: ${this.escapeHTML(
          options.include_sensitive_data ? "Full Data" : "Anonymized Data"
        )}</p>
    </div>
    ${sectionsHTML}
</body>
</html>
    `;
  }

  public async generateReport(
    data: TradingReport,
    options: ReportGenerationOptions
  ): Promise<void> {
    const timestamp = new Date().toISOString().split("T")[0];
    const filename = `exchange-hub-report-${options.time_range}-${timestamp}`;

    try {
      switch (options.format) {
        case "csv": {
          const csvContent = this.formatDataForCSV(data, options);
          downloadFile(csvContent, `${filename}.csv`, "text/csv");
          break;
        }

        case "json": {
          const sanitizedData = this.sanitizeData(data, options);
          const jsonContent = JSON.stringify(
            {
              ...sanitizedData,
              report_options: {
                time_range: options.time_range,
                sections: options.sections,
                include_sensitive_data: options.include_sensitive_data,
              },
            },
            null,
            2
          );
          downloadFile(jsonContent, `${filename}.json`, "application/json");
          break;
        }

        case "pdf": {
          const htmlContent = this.generateHTML(data, options);
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
