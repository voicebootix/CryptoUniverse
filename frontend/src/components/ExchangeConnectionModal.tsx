import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  X,
  Eye,
  EyeOff,
  AlertTriangle,
  CheckCircle,
  Shield,
  Key,
  Globe,
  HelpCircle,
  ExternalLink,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { ExchangeConnectionRequest } from "@/hooks/useExchanges";

interface ExchangeConnectionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConnect: (request: ExchangeConnectionRequest) => Promise<void>;
  connecting: boolean;
}

const EXCHANGE_INFO = {
  binance: {
    name: "Binance",
    icon: "🔶",
    color: "from-yellow-400 to-orange-500",
    permissions: ["Spot Trading", "Futures", "Margin"],
    requirements: ["API Key", "Secret Key"],
    guide:
      "https://www.binance.com/en/support/faq/how-to-create-api-key-on-binance-360002502072",
  },
  coinbase: {
    name: "Coinbase Pro",
    icon: "🔵",
    color: "from-blue-400 to-blue-600",
    permissions: ["Spot Trading", "Portfolio View"],
    requirements: ["API Key", "Secret Key", "Passphrase"],
    guide:
      "https://help.coinbase.com/en/pro/other-topics/api/how-to-create-an-api-key",
  },
  kraken: {
    name: "Kraken",
    icon: "🐙",
    color: "from-purple-400 to-purple-600",
    permissions: ["Spot Trading", "Futures", "Query Funds"],
    requirements: ["API Key", "Secret Key"],
    guide:
      "https://support.kraken.com/hc/en-us/articles/360000919966-How-to-generate-an-API-key-pair",
  },
  kucoin: {
    name: "KuCoin",
    icon: "🟢",
    color: "from-green-400 to-green-600",
    permissions: ["Spot Trading", "Futures", "General"],
    requirements: ["API Key", "Secret Key", "Passphrase"],
    guide: "https://docs.kucoin.com/#create-an-api",
  },
  bybit: {
    name: "Bybit",
    icon: "🟠",
    color: "from-orange-400 to-orange-600",
    permissions: ["Spot Trading", "Derivatives", "Read Only"],
    requirements: ["API Key", "Secret Key"],
    guide:
      "https://help.bybit.com/hc/en-us/articles/360039749613-How-to-create-a-new-API-key",
  },
};

const ExchangeConnectionModal: React.FC<ExchangeConnectionModalProps> = ({
  isOpen,
  onClose,
  onConnect,
  connecting,
}) => {
  const [selectedExchange, setSelectedExchange] = useState<string>("");
  const [formData, setFormData] = useState({
    api_key: "",
    secret_key: "",
    passphrase: "",
    nickname: "",
    sandbox: false,
  });
  const [showSecrets, setShowSecrets] = useState({
    api_key: false,
    secret_key: false,
    passphrase: false,
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [step, setStep] = useState<"select" | "configure">("select");

  const resetForm = () => {
    setFormData({
      api_key: "",
      secret_key: "",
      passphrase: "",
      nickname: "",
      sandbox: false,
    });
    setErrors({});
    setSelectedExchange("");
    setStep("select");
  };

  const handleClose = () => {
    resetForm();
    onClose();
  };

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    if (!formData.api_key.trim()) {
      newErrors.api_key = "API Key is required";
    } else if (formData.api_key.length < 10) {
      newErrors.api_key = "API Key must be at least 10 characters";
    }

    if (!formData.secret_key.trim()) {
      newErrors.secret_key = "Secret Key is required";
    } else if (formData.secret_key.length < 10) {
      newErrors.secret_key = "Secret Key must be at least 10 characters";
    }

    const exchangeInfo =
      EXCHANGE_INFO[selectedExchange as keyof typeof EXCHANGE_INFO];
    if (
      exchangeInfo?.requirements.includes("Passphrase") &&
      !formData.passphrase.trim()
    ) {
      newErrors.passphrase = "Passphrase is required for this exchange";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleConnect = async () => {
    if (!validateForm()) return;

    try {
      await onConnect({
        exchange: selectedExchange,
        api_key: formData.api_key,
        secret_key: formData.secret_key,
        passphrase: formData.passphrase || undefined,
        sandbox: formData.sandbox,
        nickname: formData.nickname || undefined,
      });

      handleClose();
    } catch (error) {
      console.error("Connection failed:", error);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="w-full max-w-2xl max-h-[90vh] overflow-y-auto"
      >
        <Card className="p-0 bg-[#1a1c23] border-[#2a2d35] relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 to-purple-500/5"></div>
          <div className="relative">
            {/* Header */}
            <div className="flex justify-between items-center p-6 border-b border-[#2a2d35]">
              <div>
                <h2 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent flex items-center gap-3">
                  <Globe className="w-6 h-6 text-blue-400" />
                  Connect Exchange
                </h2>
                <p className="text-gray-400 mt-1">
                  {step === "select"
                    ? "Choose an exchange to connect"
                    : "Enter your API credentials"}
                </p>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={handleClose}
                className="bg-[#1e2128] border-[#2a2d35] text-gray-400 hover:text-gray-200"
              >
                <X className="w-4 h-4" />
              </Button>
            </div>

            {step === "select" && (
              <div className="p-6 space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {Object.entries(EXCHANGE_INFO).map(([key, info]) => (
                    <motion.div
                      key={key}
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      className={`p-6 bg-[#1e2128] border rounded-lg cursor-pointer transition-all ${
                        selectedExchange === key
                          ? "border-blue-500/50 shadow-lg shadow-blue-500/10"
                          : "border-[#2a2d35] hover:border-[#3a3d45]"
                      }`}
                      onClick={() => setSelectedExchange(key)}
                    >
                      <div className="flex items-center gap-3 mb-4">
                        <div className="w-12 h-12 flex items-center justify-center bg-[#1a1c23] rounded-xl border border-[#2a2d35]">
                          <span className="text-2xl">{info.icon}</span>
                        </div>
                        <div>
                          <h3 className="font-semibold text-gray-200">
                            {info.name}
                          </h3>
                          <div className="flex gap-1 mt-1">
                            {info.permissions.slice(0, 2).map((perm) => (
                              <Badge
                                key={perm}
                                variant="secondary"
                                className="bg-blue-500/10 text-blue-400 border-blue-500/20 text-xs"
                              >
                                {perm}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      </div>

                      <div className="text-sm text-gray-400">
                        <p className="mb-2">Required:</p>
                        <div className="flex flex-wrap gap-1">
                          {info.requirements.map((req) => (
                            <Badge
                              key={req}
                              variant="outline"
                              className="bg-[#1a1c23] border-[#2a2d35] text-gray-300 text-xs"
                            >
                              {req}
                            </Badge>
                          ))}
                        </div>
                      </div>

                      <a
                        href={info.guide}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 mt-3"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <HelpCircle className="w-3 h-3" />
                        Setup Guide
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    </motion.div>
                  ))}
                </div>

                <div className="flex justify-end pt-4 border-t border-[#2a2d35]">
                  <Button
                    onClick={() => setStep("configure")}
                    disabled={!selectedExchange}
                    className="px-8 bg-gradient-to-r from-blue-600 to-purple-600 text-white hover:shadow-lg hover:shadow-blue-500/20"
                  >
                    Continue
                  </Button>
                </div>
              </div>
            )}

            {step === "configure" && selectedExchange && (
              <div className="space-y-6">
                {/* Exchange Header */}
                <div className="flex items-center gap-3 p-6 bg-[#1e2128] border-b border-[#2a2d35]">
                  <div className="w-12 h-12 flex items-center justify-center bg-[#1a1c23] rounded-xl border border-[#2a2d35]">
                    <span className="text-2xl">
                      {
                        EXCHANGE_INFO[
                          selectedExchange as keyof typeof EXCHANGE_INFO
                        ].icon
                      }
                    </span>
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold text-gray-200">
                      {
                        EXCHANGE_INFO[
                          selectedExchange as keyof typeof EXCHANGE_INFO
                        ].name
                      }
                    </h3>
                    <p className="text-sm text-gray-400">
                      Enter your API credentials to connect
                    </p>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      // Clear sensitive fields when going back
                      setFormData(prev => ({
                        ...prev,
                        api_key: "",
                        secret_key: "",
                        passphrase: ""
                      }));
                      setErrors({});
                      setStep("select");
                    }}
                    className="bg-[#1a1c23] border-[#2a2d35] text-gray-300 hover:text-gray-200"
                  >
                    Change Exchange
                  </Button>
                </div>

                {/* Security Notice */}
                <div className="mx-6 p-4 bg-blue-500/5 border border-blue-500/20 rounded-lg">
                  <div className="flex items-start gap-3">
                    <Shield className="w-5 h-5 text-blue-400 mt-0.5" />
                    <div>
                      <h4 className="font-medium text-blue-400 mb-1">
                        Security Notice
                      </h4>
                      <p className="text-sm text-gray-400">
                        Your API keys are encrypted and stored securely. We
                        recommend using read-only or trading-only permissions.
                        Never share keys with withdraw permissions.
                      </p>
                    </div>
                  </div>
                </div>

                {/* Form Fields */}
                <div className="px-6 space-y-4">
                  <div>
                    <Label htmlFor="nickname" className="text-gray-300">
                      Connection Nickname (Optional)
                    </Label>
                    <Input
                      id="nickname"
                      placeholder="e.g. Main Trading Account"
                      value={formData.nickname}
                      onChange={(e) =>
                        setFormData((prev) => ({
                          ...prev,
                          nickname: e.target.value,
                        }))
                      }
                      className="bg-[#1e2128] border-[#2a2d35] text-gray-200 placeholder:text-gray-500"
                    />
                  </div>

                  <div>
                    <Label
                      htmlFor="api_key"
                      className="flex items-center gap-2 text-gray-300"
                    >
                      <Key className="w-4 h-4 text-blue-400" />
                      API Key *
                    </Label>
                    <div className="relative">
                      <Input
                        id="api_key"
                        type={showSecrets.api_key ? "text" : "password"}
                        placeholder="Enter your API key"
                        value={formData.api_key}
                        onChange={(e) =>
                          setFormData((prev) => ({
                            ...prev,
                            api_key: e.target.value,
                          }))
                        }
                        className={`bg-[#1e2128] border-[#2a2d35] text-gray-200 placeholder:text-gray-500 ${
                          errors.api_key ? "border-red-500" : ""
                        }`}
                      />
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-200"
                        onClick={() =>
                          setShowSecrets((prev) => ({
                            ...prev,
                            api_key: !prev.api_key,
                          }))
                        }
                      >
                        {showSecrets.api_key ? (
                          <EyeOff className="w-4 h-4" />
                        ) : (
                          <Eye className="w-4 h-4" />
                        )}
                      </Button>
                    </div>
                    {errors.api_key && (
                      <p className="text-sm text-red-400 mt-1">
                        {errors.api_key}
                      </p>
                    )}
                  </div>

                  <div>
                    <Label
                      htmlFor="secret_key"
                      className="flex items-center gap-2 text-gray-300"
                    >
                      <Shield className="w-4 h-4 text-purple-400" />
                      Secret Key *
                    </Label>
                    <div className="relative">
                      <Input
                        id="secret_key"
                        type={showSecrets.secret_key ? "text" : "password"}
                        placeholder="Enter your secret key"
                        value={formData.secret_key}
                        onChange={(e) =>
                          setFormData((prev) => ({
                            ...prev,
                            secret_key: e.target.value,
                          }))
                        }
                        className={`bg-[#1e2128] border-[#2a2d35] text-gray-200 placeholder:text-gray-500 ${
                          errors.secret_key ? "border-red-500" : ""
                        }`}
                      />
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-200"
                        onClick={() =>
                          setShowSecrets((prev) => ({
                            ...prev,
                            secret_key: !prev.secret_key,
                          }))
                        }
                      >
                        {showSecrets.secret_key ? (
                          <EyeOff className="w-4 h-4" />
                        ) : (
                          <Eye className="w-4 h-4" />
                        )}
                      </Button>
                    </div>
                    {errors.secret_key && (
                      <p className="text-sm text-red-400 mt-1">
                        {errors.secret_key}
                      </p>
                    )}
                  </div>

                  {EXCHANGE_INFO[
                    selectedExchange as keyof typeof EXCHANGE_INFO
                  ].requirements.includes("Passphrase") && (
                    <div>
                      <Label
                        htmlFor="passphrase"
                        className="flex items-center gap-2 text-gray-300"
                      >
                        <Key className="w-4 h-4 text-green-400" />
                        Passphrase *
                      </Label>
                      <div className="relative">
                        <Input
                          id="passphrase"
                          type={showSecrets.passphrase ? "text" : "password"}
                          placeholder="Enter your passphrase"
                          value={formData.passphrase}
                          onChange={(e) =>
                            setFormData((prev) => ({
                              ...prev,
                              passphrase: e.target.value,
                            }))
                          }
                          className={`bg-[#1e2128] border-[#2a2d35] text-gray-200 placeholder:text-gray-500 ${
                            errors.passphrase ? "border-red-500" : ""
                          }`}
                        />
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-200"
                          onClick={() =>
                            setShowSecrets((prev) => ({
                              ...prev,
                              passphrase: !prev.passphrase,
                            }))
                          }
                        >
                          {showSecrets.passphrase ? (
                            <EyeOff className="w-4 h-4" />
                          ) : (
                            <Eye className="w-4 h-4" />
                          )}
                        </Button>
                      </div>
                      {errors.passphrase && (
                        <p className="text-sm text-red-400 mt-1">
                          {errors.passphrase}
                        </p>
                      )}
                    </div>
                  )}

                  <div className="flex items-center justify-between p-4 bg-[#1e2128] border border-[#2a2d35] rounded-lg">
                    <div>
                      <Label htmlFor="sandbox" className="text-gray-300">
                        Sandbox Mode
                      </Label>
                      <p className="text-sm text-gray-400">
                        Use test environment for development
                      </p>
                    </div>
                    <Switch
                      id="sandbox"
                      checked={formData.sandbox}
                      onCheckedChange={(checked) =>
                        setFormData((prev) => ({ ...prev, sandbox: checked }))
                      }
                      className="data-[state=checked]:bg-blue-600"
                    />
                  </div>
                </div>

                {/* Actions */}
                <div className="flex justify-end gap-3 p-6 border-t border-[#2a2d35] bg-[#1e2128]">
                  <Button
                    variant="outline"
                    onClick={() => {
                      // Clear sensitive fields when going back
                      setFormData(prev => ({
                        ...prev,
                        api_key: "",
                        secret_key: "",
                        passphrase: ""
                      }));
                      setErrors({});
                      setStep("select");
                    }}
                    className="bg-[#1a1c23] border-[#2a2d35] text-gray-300 hover:text-gray-200"
                  >
                    Back
                  </Button>
                  <Button
                    onClick={handleConnect}
                    disabled={connecting}
                    className="px-8 bg-gradient-to-r from-blue-600 to-purple-600 text-white hover:shadow-lg hover:shadow-blue-500/20"
                  >
                    {connecting ? (
                      <>
                        <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin mr-2" />
                        Connecting...
                      </>
                    ) : (
                      "Connect Exchange"
                    )}
                  </Button>
                </div>
              </div>
            )}
          </div>
        </Card>
      </motion.div>
    </div>
  );
};

export default ExchangeConnectionModal;
