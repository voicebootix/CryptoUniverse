import React, { useState } from "react";
import { motion } from "framer-motion";
import {
  Download,
  FileJson,
  FileText,
  FileImage,
  X,
  Calendar,
  Eye,
  EyeOff,
  Layers,
} from "lucide-react";
import { Card } from "./ui/card";
import { Button } from "./ui/button";
import { Label } from "./ui/label";
import { Switch } from "./ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./ui/select";
import { ReportFormat, ReportGenerationOptions } from "@/types/reports";
import { useToast } from "./ui/use-toast";

interface ExportReportModalProps {
  isOpen: boolean;
  onClose: () => void;
  onExport: (options: ReportGenerationOptions) => Promise<void>;
}

const ExportReportModal: React.FC<ExportReportModalProps> = ({
  isOpen,
  onClose,
  onExport,
}) => {
  const { toast } = useToast();
  const [exporting, setExporting] = useState(false);
  const [options, setOptions] = useState<ReportGenerationOptions>({
    format: "pdf",
    include_sensitive_data: false,
    time_range: "24h",
    sections: ["overview", "exchanges", "arbitrage", "performance"],
  });

  const handleExport = async () => {
    setExporting(true);
    try {
      await onExport(options);
      toast({
        title: "Report Generated",
        description:
          "Your report has been generated and downloaded successfully.",
        variant: "default",
      });
      onClose();
    } catch (error) {
      toast({
        title: "Export Failed",
        description: "Failed to generate report. Please try again.",
        variant: "destructive",
      });
    } finally {
      setExporting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="w-full max-w-lg"
      >
        <Card className="p-0 bg-[#1a1c23] border-[#2a2d35] relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 to-purple-500/5"></div>
          <div className="relative">
            {/* Header */}
            <div className="flex justify-between items-center p-6 border-b border-[#2a2d35]">
              <div>
                <h2 className="text-2xl font-bold flex items-center gap-3 bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
                  <Download className="w-6 h-6 text-blue-400" />
                  Export Report
                </h2>
                <p className="text-gray-400 mt-1">
                  Configure and download your trading report
                </p>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={onClose}
                className="hover:bg-[#1e2128] text-gray-400 hover:text-gray-200"
              >
                <X className="w-4 h-4" />
              </Button>
            </div>

            {/* Content */}
            <div className="p-6 space-y-6">
              {/* Format Selection */}
              <div className="space-y-4">
                <Label className="text-gray-300">Report Format</Label>
                <div className="grid grid-cols-3 gap-4">
                  <Button
                    variant={options.format === "pdf" ? "default" : "outline"}
                    className={`flex-col h-24 ${
                      options.format === "pdf"
                        ? "bg-gradient-to-br from-blue-600 to-purple-600"
                        : "hover:bg-[#1e2128]"
                    }`}
                    onClick={() => setOptions({ ...options, format: "pdf" })}
                  >
                    <FileImage className="w-8 h-8 mb-2" />
                    PDF
                  </Button>
                  <Button
                    variant={options.format === "csv" ? "default" : "outline"}
                    className={`flex-col h-24 ${
                      options.format === "csv"
                        ? "bg-gradient-to-br from-blue-600 to-purple-600"
                        : "hover:bg-[#1e2128]"
                    }`}
                    onClick={() => setOptions({ ...options, format: "csv" })}
                  >
                    <FileText className="w-8 h-8 mb-2" />
                    CSV
                  </Button>
                  <Button
                    variant={options.format === "json" ? "default" : "outline"}
                    className={`flex-col h-24 ${
                      options.format === "json"
                        ? "bg-gradient-to-br from-blue-600 to-purple-600"
                        : "hover:bg-[#1e2128]"
                    }`}
                    onClick={() => setOptions({ ...options, format: "json" })}
                  >
                    <FileJson className="w-8 h-8 mb-2" />
                    JSON
                  </Button>
                </div>
              </div>

              {/* Time Range */}
              <div className="space-y-2">
                <Label className="text-gray-300">Time Range</Label>
                <Select
                  value={options.time_range}
                  onValueChange={(value: "24h" | "7d" | "30d" | "all") =>
                    setOptions({ ...options, time_range: value })
                  }
                >
                  <SelectTrigger className="bg-[#1a1c23] border-[#2a2d35] text-gray-200">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-[#1a1c23] border-[#2a2d35]">
                    <SelectItem value="24h">Last 24 Hours</SelectItem>
                    <SelectItem value="7d">Last 7 Days</SelectItem>
                    <SelectItem value="30d">Last 30 Days</SelectItem>
                    <SelectItem value="all">All Time</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Sections */}
              <div className="space-y-2">
                <Label className="text-gray-300">Include Sections</Label>
                <div className="space-y-3 mt-2">
                  <div className="flex items-center justify-between p-3 bg-[#1e2128] border border-[#2a2d35] rounded-lg">
                    <div className="flex items-center gap-2">
                      <Layers className="w-4 h-4" />
                      <span>Overview</span>
                    </div>
                    <Switch
                      checked={options.sections.includes("overview")}
                      onCheckedChange={(checked) =>
                        setOptions({
                          ...options,
                          sections: checked
                            ? [...options.sections, "overview"]
                            : options.sections.filter((s) => s !== "overview"),
                        })
                      }
                    />
                  </div>
                  <div className="flex items-center justify-between p-3 bg-[#1e2128] border border-[#2a2d35] rounded-lg">
                    <div className="flex items-center gap-2">
                      <Layers className="w-4 h-4" />
                      <span>Exchange Performance</span>
                    </div>
                    <Switch
                      checked={options.sections.includes("exchanges")}
                      onCheckedChange={(checked) =>
                        setOptions({
                          ...options,
                          sections: checked
                            ? [...options.sections, "exchanges"]
                            : options.sections.filter((s) => s !== "exchanges"),
                        })
                      }
                    />
                  </div>
                  <div className="flex items-center justify-between p-3 bg-[#1e2128] border border-[#2a2d35] rounded-lg">
                    <div className="flex items-center gap-2">
                      <Layers className="w-4 h-4" />
                      <span>Arbitrage Opportunities</span>
                    </div>
                    <Switch
                      checked={options.sections.includes("arbitrage")}
                      onCheckedChange={(checked) =>
                        setOptions({
                          ...options,
                          sections: checked
                            ? [...options.sections, "arbitrage"]
                            : options.sections.filter((s) => s !== "arbitrage"),
                        })
                      }
                    />
                  </div>
                  <div className="flex items-center justify-between p-3 bg-[#1e2128] border border-[#2a2d35] rounded-lg">
                    <div className="flex items-center gap-2">
                      <Layers className="w-4 h-4" />
                      <span>Performance Analysis</span>
                    </div>
                    <Switch
                      checked={options.sections.includes("performance")}
                      onCheckedChange={(checked) =>
                        setOptions({
                          ...options,
                          sections: checked
                            ? [...options.sections, "performance"]
                            : options.sections.filter(
                                (s) => s !== "performance"
                              ),
                        })
                      }
                    />
                  </div>
                </div>
              </div>

              {/* Sensitive Data Toggle */}
              <div className="flex items-center justify-between p-4 bg-[#1e2128] border border-[#2a2d35] rounded-lg">
                <div>
                  <Label className="text-gray-300 flex items-center gap-2">
                    {options.include_sensitive_data ? (
                      <Eye className="w-4 h-4" />
                    ) : (
                      <EyeOff className="w-4 h-4" />
                    )}
                    Include Sensitive Data
                  </Label>
                  <p className="text-sm text-gray-500">
                    Include API keys, balances and other sensitive information
                  </p>
                </div>
                <Switch
                  checked={options.include_sensitive_data}
                  onCheckedChange={(checked) =>
                    setOptions({ ...options, include_sensitive_data: checked })
                  }
                />
              </div>
            </div>

            {/* Footer */}
            <div className="flex justify-end items-center p-6 border-t border-[#2a2d35]">
              <div className="flex gap-3">
                <Button
                  variant="outline"
                  onClick={onClose}
                  className="bg-[#1a1c23] text-gray-300 border-[#2a2d35] hover:bg-[#1e2128] hover:text-gray-200"
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleExport}
                  disabled={exporting || options.sections.length === 0}
                  className="px-8 bg-gradient-to-r from-blue-600 to-purple-600 text-white hover:from-blue-700 hover:to-purple-700"
                >
                  {exporting ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin mr-2" />
                      Exporting...
                    </>
                  ) : (
                    <>
                      <Download className="w-4 h-4 mr-2" />
                      Export Report
                    </>
                  )}
                </Button>
              </div>
            </div>
          </div>
        </Card>
      </motion.div>
    </div>
  );
};

export default ExportReportModal;
