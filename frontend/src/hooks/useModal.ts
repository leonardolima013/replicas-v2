import { useState, useCallback } from "react";
import type { ModalType } from "../components/Modal";

interface ModalState {
  isOpen: boolean;
  title?: string;
  message: string;
  type: ModalType;
  confirmText?: string;
  cancelText?: string;
  onConfirm?: () => void;
}

export function useModal() {
  const [modalState, setModalState] = useState<ModalState>({
    isOpen: false,
    message: "",
    type: "info",
  });

  const closeModal = useCallback(() => {
    setModalState((prev) => ({ ...prev, isOpen: false }));
  }, []);

  const showAlert = useCallback(
    (message: string, type: ModalType = "info", title?: string) => {
      setModalState({
        isOpen: true,
        message,
        type,
        title,
        confirmText: "OK",
      });
    },
    [],
  );

  const showConfirm = useCallback(
    (
      message: string,
      onConfirm: () => void,
      title?: string,
      confirmText: string = "Confirmar",
      cancelText: string = "Cancelar",
    ) => {
      setModalState({
        isOpen: true,
        message,
        type: "confirm",
        title,
        confirmText,
        cancelText,
        onConfirm,
      });
    },
    [],
  );

  const showSuccess = useCallback(
    (message: string, title?: string) => {
      showAlert(message, "success", title);
    },
    [showAlert],
  );

  const showError = useCallback(
    (message: string, title?: string) => {
      showAlert(message, "error", title);
    },
    [showAlert],
  );

  const showWarning = useCallback(
    (message: string, title?: string) => {
      showAlert(message, "warning", title);
    },
    [showAlert],
  );

  return {
    modalState,
    closeModal,
    showAlert,
    showConfirm,
    showSuccess,
    showError,
    showWarning,
  };
}
