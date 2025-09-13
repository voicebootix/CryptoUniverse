/**
 * CSV Export Utility
 * 
 * Provides a reusable function to export data as CSV with proper formatting
 * and Excel compatibility.
 */

interface CsvExportOptions {
  filename?: string;
  includeUtf8Bom?: boolean;
  dateFormat?: 'iso' | 'localized';
}

/**
 * Escapes CSV field values by wrapping in double quotes and escaping existing quotes
 */
function escapeCsvField(field: any): string {
  if (field === null || field === undefined) {
    return '';
  }
  
  let value = String(field);
  
  // If field contains comma, newline, or double quote, wrap in quotes
  if (value.includes(',') || value.includes('\n') || value.includes('\r') || value.includes('"')) {
    // Escape existing double quotes by doubling them
    value = value.replace(/"/g, '""');
    value = `"${value}"`;
  }
  
  return value;
}

/**
 * Converts an array of objects to CSV format
 */
export function exportCsv(
  data: any[],
  headers: string[],
  options: CsvExportOptions = {}
): void {
  const {
    filename = 'export.csv',
    includeUtf8Bom = true,
    dateFormat = 'localized'
  } = options;

  if (!data || data.length === 0) {
    throw new Error('No data to export');
  }

  // Build CSV content
  let csvContent = '';
  
  // Add UTF-8 BOM for Excel compatibility
  if (includeUtf8Bom) {
    csvContent = '\ufeff';
  }
  
  // Add headers
  csvContent += headers.map(header => escapeCsvField(header)).join(',') + '\r\n';
  
  // Add data rows
  data.forEach(row => {
    const rowData = headers.map(header => {
      let value = row[header];
      
      // Format dates consistently
      if (value instanceof Date) {
        value = dateFormat === 'iso' 
          ? value.toISOString() 
          : value.toLocaleDateString();
      } else if (typeof value === 'string' && value.match(/^\d{4}-\d{2}-\d{2}T/)) {
        // Handle ISO date strings
        const date = new Date(value);
        value = dateFormat === 'iso' 
          ? date.toISOString() 
          : date.toLocaleDateString();
      }
      
      return escapeCsvField(value);
    });
    
    csvContent += rowData.join(',') + '\r\n';
  });
  
  // Create and trigger download
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  
  if (link.download !== undefined) {
    // Create object URL and trigger download
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', filename);
    link.style.visibility = 'hidden';
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    // Clean up object URL
    URL.revokeObjectURL(url);
  } else {
    throw new Error('CSV download not supported in this browser');
  }
}

/**
 * Export credit transactions to CSV
 */
export function exportCreditTransactionsCsv(transactions: any[]): void {
  const headers = [
    'id',
    'description', 
    'amount',
    'transaction_type',
    'status',
    'created_at',
    'processed_at'
  ];
  
  const processedData = transactions.map(tx => ({
    id: tx.id,
    description: tx.description,
    amount: tx.amount,
    transaction_type: tx.transaction_type,
    status: tx.status,
    created_at: tx.created_at,
    processed_at: tx.processed_at || 'N/A'
  }));
  
  exportCsv(processedData, headers, {
    filename: `credit_transactions_${new Date().toISOString().split('T')[0]}.csv`,
    includeUtf8Bom: true,
    dateFormat: 'localized'
  });
}