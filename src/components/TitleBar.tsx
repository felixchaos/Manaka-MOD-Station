import { MouseEvent, useEffect, useState } from "react";
import {
  SubtractRegular,
  SquareRegular,
  DismissRegular,
} from "@fluentui/react-icons";
import { getCurrentWindow, Window } from "@tauri-apps/api/window";
import appIcon from "../assets/app-icon.png";

interface TitleBarProps {
  isDark: boolean;
}

export function TitleBar({ isDark }: TitleBarProps) {
  const [win, setWin] = useState<Window | null>(null);

  useEffect(() => {
    try {
      setWin(getCurrentWindow());
    } catch {
      setWin(null);
    }
  }, []);

  const handleMinimize = async () => {
    if (!win) return;
    await win.minimize();
  };

  const handleToggleMaximize = async () => {
    if (!win) return;
    await win.toggleMaximize();
  };

  const handleClose = async () => {
    if (!win) return;
    await win.close();
  };

  const handleTitlebarDoubleClick = (event: MouseEvent<HTMLDivElement>) => {
    if ((event.target as HTMLElement).closest(".titlebar__actions")) {
      return;
    }
    void handleToggleMaximize();
  };

  const handleStartDragging = async (event: MouseEvent<HTMLDivElement>) => {
    if (!win || event.button !== 0) {
      return;
    }
    if ((event.target as HTMLElement).closest(".titlebar__actions")) {
      return;
    }
    await win.startDragging();
  };

  return (
    <div className={`titlebar ${isDark ? "titlebar--dark" : "titlebar--light"}`} onDoubleClick={handleTitlebarDoubleClick}>
      <div className="titlebar__brand titlebar__drag" data-tauri-drag-region onMouseDown={(event) => void handleStartDragging(event)}>
        <img className="titlebar__icon" src={appIcon} alt="" draggable={false} />
        <span className="titlebar__title">Manaka MOD Station</span>
      </div>

      <div className="titlebar__actions titlebar__nodrag">
        <button
          type="button"
          onClick={() => void handleMinimize()}
          className="titlebar__button titlebar__nodrag"
          title="最小化"
          aria-label="最小化"
        >
          <SubtractRegular fontSize={12} />
        </button>

        <button
          type="button"
          onClick={() => void handleToggleMaximize()}
          className="titlebar__button titlebar__nodrag"
          title="最大化"
          aria-label="最大化"
        >
          <SquareRegular fontSize={12} />
        </button>

        <button
          type="button"
          onClick={() => void handleClose()}
          className="titlebar__button titlebar__button--close titlebar__nodrag"
          title="关闭"
          aria-label="关闭"
        >
          <DismissRegular fontSize={12} />
        </button>
      </div>
    </div>
  );
}
