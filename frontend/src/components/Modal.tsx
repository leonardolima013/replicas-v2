import { useEffect } from "react";
import {
  AlertCircle,
  CheckCircle2,
  AlertTriangle,
  Info,
  X,
} from "lucide-react";

export type ModalType = "info" | "success" | "warning" | "error" | "confirm";

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm?: () => void;
  title?: string;
  message: string;
  type?: ModalType;
  confirmText?: string;
  cancelText?: string;
}

export default function Modal({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  type = "info",
  confirmText = "OK",
  cancelText = "Cancelar",
}: ModalProps) {
  // Fechar com tecla ESC
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener("keydown", handleEscape);
      // Prevenir scroll do body quando modal está aberto
      document.body.style.overflow = "hidden";
    }

    return () => {
      document.removeEventListener("keydown", handleEscape);
      document.body.style.overflow = "unset";
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const getIcon = () => {
    switch (type) {
      case "success":
        return <CheckCircle2 className="w-6 h-6 text-emerald-500" />;
      case "warning":
        return <AlertTriangle className="w-6 h-6 text-yellow-500" />;
      case "error":
        return <AlertCircle className="w-6 h-6 text-rose-500" />;
      case "confirm":
        return <AlertCircle className="w-6 h-6 text-blue-500" />;
      default:
        return <Info className="w-6 h-6 text-blue-500" />;
    }
  };

  const getStyles = () => {
    switch (type) {
      case "success":
        return {
          bg: "bg-emerald-900/20",
          border: "border-emerald-500/50",
          titleColor: "text-emerald-400",
          messageColor: "text-emerald-300",
          buttonBg: "bg-emerald-600 hover:bg-emerald-700",
        };
      case "warning":
        return {
          bg: "bg-yellow-900/20",
          border: "border-yellow-500/50",
          titleColor: "text-yellow-400",
          messageColor: "text-yellow-300",
          buttonBg: "bg-yellow-600 hover:bg-yellow-700",
        };
      case "error":
        return {
          bg: "bg-rose-900/20",
          border: "border-rose-500/50",
          titleColor: "text-rose-400",
          messageColor: "text-rose-300",
          buttonBg: "bg-rose-600 hover:bg-rose-700",
        };
      case "confirm":
        return {
          bg: "bg-blue-900/20",
          border: "border-blue-500/50",
          titleColor: "text-blue-400",
          messageColor: "text-blue-300",
          buttonBg: "bg-blue-600 hover:bg-blue-700",
        };
      default:
        return {
          bg: "bg-zinc-800/50",
          border: "border-zinc-600",
          titleColor: "text-zinc-100",
          messageColor: "text-zinc-300",
          buttonBg: "bg-zinc-600 hover:bg-zinc-700",
        };
    }
  };

  const styles = getStyles();
  const defaultTitle = title || (type === "confirm" ? "Confirmação" : "Aviso");

  const handleConfirm = () => {
    if (onConfirm) {
      onConfirm();
    }
    onClose();
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-200"
      onClick={onClose}
    >
      <div
        className={`${styles.bg} ${styles.border} border-2 rounded-xl shadow-2xl max-w-md w-full transform animate-in zoom-in-95 duration-200`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between p-6 pb-4">
          <div className="flex items-start gap-3 flex-1">
            <div className="flex-shrink-0 mt-0.5">{getIcon()}</div>
            <div className="flex-1">
              <h3 className={`text-lg font-semibold ${styles.titleColor}`}>
                {defaultTitle}
              </h3>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-zinc-400 hover:text-zinc-100 transition-colors flex-shrink-0 ml-2"
            aria-label="Fechar"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="px-6 pb-6">
          <p className={`text-sm ${styles.messageColor} whitespace-pre-line`}>
            {message}
          </p>
        </div>

        {/* Footer */}
        <div className="flex gap-3 px-6 pb-6 pt-2">
          {type === "confirm" && (
            <button
              onClick={onClose}
              className="flex-1 px-4 py-2.5 bg-zinc-700 hover:bg-zinc-600 text-zinc-100 rounded-lg font-medium transition-colors"
            >
              {cancelText}
            </button>
          )}
          <button
            onClick={handleConfirm}
            className={`flex-1 px-4 py-2.5 ${styles.buttonBg} text-white rounded-lg font-medium transition-colors`}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
}
