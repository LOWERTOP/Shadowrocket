// Run from the repository root: swift tests/validate_adblocking_icu.swift
// Check Foundation/ICU regex behavior; this is not a Shadowrocket import test.
import Foundation

let root = URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
let data = try Data(contentsOf: root.appendingPathComponent("tests/fixtures/adblocking_urls.json"))
let fixtures = try JSONSerialization.jsonObject(with: data) as! [String: [String: Any]]
var checked = 0
for (name, item) in fixtures {
    let file = root.appendingPathComponent("modules/adblocking/\(name).sgmodule")
    let text = try String(contentsOf: file, encoding: .utf8)
    let section = text.components(separatedBy: "[URL Rewrite]\n")[1]
        .components(separatedBy: "\n[MITM]")[0]
    let patterns = try section.components(separatedBy: .newlines)
        .filter { !$0.isEmpty && !$0.hasPrefix("#") }
        .map { try NSRegularExpression(pattern: $0.components(separatedBy: " - ")[0]) }
    for (key, expected) in [("positive", true), ("negative", false)] {
        for url in item[key] as! [String] {
            let range = NSRange(url.startIndex..<url.endIndex, in: url)
            let matched = patterns.contains { $0.firstMatch(in: url, range: range) != nil }
            guard matched == expected else {
                fatalError("\(name): unexpected match=\(matched) for \(url)")
            }
            checked += 1
        }
    }
}
print("Foundation/ICU: \(checked) URL cases passed across \(fixtures.count) modules")
