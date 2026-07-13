import yaml from "js-yaml";
import type { ScannerConfig } from "./types";

export function configToYaml(config: ScannerConfig): string {
  return yaml.dump(config, { lineWidth: 100, noRefs: true });
}

export function yamlToConfig(text: string): ScannerConfig {
  return yaml.load(text) as ScannerConfig;
}

export function linesToList(text: string): string[] {
  return text
    .split("\n")
    .map((s) => s.trim())
    .filter(Boolean);
}

export function listToLines(list: string[]): string {
  return list.join("\n");
}
