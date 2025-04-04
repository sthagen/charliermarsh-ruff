import { Diagnostic } from "ruff_wasm";
import classNames from "classnames";
import { Theme } from "shared";
import { useMemo } from "react";

interface Props {
  diagnostics: Diagnostic[];
  theme: Theme;

  onGoTo(line: number, column: number): void;
}

export default function Diagnostics({
  diagnostics: unsorted,
  theme,
  onGoTo,
}: Props) {
  const diagnostics = useMemo(() => {
    const sorted = [...unsorted];
    sorted.sort((a, b) => {
      if (a.start_location.row === b.start_location.row) {
        return a.start_location.column - b.start_location.column;
      }

      return a.start_location.row - b.start_location.row;
    });

    return sorted;
  }, [unsorted]);

  return (
    <div
      className={classNames(
        "flex grow flex-col overflow-hidden",
        theme === "dark" ? "text-white" : null,
      )}
    >
      <div
        className={classNames(
          "border-b border-gray-200 px-2 py-1",
          theme === "dark" ? "border-rock" : null,
        )}
      >
        Diagnostics ({diagnostics.length})
      </div>

      <div className="flex grow p-2 overflow-hidden">
        <Items diagnostics={diagnostics} onGoTo={onGoTo} />
      </div>
    </div>
  );
}

function Items({
  diagnostics,
  onGoTo,
}: {
  diagnostics: Array<Diagnostic>;
  onGoTo(line: number, column: number): void;
}) {
  if (diagnostics.length === 0) {
    return (
      <div className={"flex flex-auto flex-col justify-center  items-center"}>
        Everything is looking good!
      </div>
    );
  }

  return (
    <ul className="space-y-0.5 grow overflow-y-scroll">
      {diagnostics.map((diagnostic, index) => {
        return (
          <li
            key={`${diagnostic.start_location.row}:${diagnostic.start_location.column}-${diagnostic.code ?? index}`}
          >
            <button
              onClick={() =>
                onGoTo(
                  diagnostic.start_location.row,
                  diagnostic.start_location.column,
                )
              }
              className="w-full text-start cursor-pointer select-text"
            >
              {diagnostic.message}{" "}
              <span className="text-gray-500">
                {diagnostic.code != null && `(${diagnostic.code})`} [Ln{" "}
                {diagnostic.start_location.row}, Col{" "}
                {diagnostic.start_location.column}]
              </span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
