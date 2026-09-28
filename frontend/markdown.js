(function () {
    "use strict";

    function escapeHtml(value) {
        return String(value == null ? "" : value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/\"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    function safeUrl(value) {
        var url = String(value || "").trim();
        if (/^(https?:\/\/|mailto:)/i.test(url)) {
            return escapeHtml(url);
        }
        return "";
    }

    function inlineMarkdown(value) {
        var text = escapeHtml(value);
        var code = [];

        text = text.replace(/`([^`\n]+)`/g, function (_, content) {
            var index = code.length;
            code.push("<code>" + content + "</code>");
            return "@@INLINE_CODE_" + index + "@@";
        });
        text = text.replace(/!\[([^\]]*)\]\(([^\s)]+)(?:\s+\"[^\"]*\")?\)/g, function (_, alt, url) {
            var safe = safeUrl(url);
            return safe ? "<img src=\"" + safe + "\" alt=\"" + escapeHtml(alt) + "\" loading=\"lazy\">" : escapeHtml(alt);
        });
        text = text.replace(/\[([^\]]+)\]\(([^\s)]+)(?:\s+\"[^\"]*\")?\)/g, function (_, label, url) {
            var safe = safeUrl(url);
            return safe ? "<a href=\"" + safe + "\" target=\"_blank\" rel=\"noopener noreferrer\">" + label + "</a>" : label;
        });
        text = text.replace(/\*\*([^*\n]+)\*\*/g, "<strong>$1</strong>");
        text = text.replace(/__([^_\n]+)__/g, "<strong>$1</strong>");
        text = text.replace(/(^|[^*])\*([^*\n]+)\*(?!\*)/g, "$1<em>$2</em>");
        text = text.replace(/(^|[^_])_([^_\n]+)_(?!_)/g, "$1<em>$2</em>");
        text = text.replace(/~~([^~\n]+)~~/g, "<del>$1</del>");
        text = text.replace(/@@INLINE_CODE_(\d+)@@/g, function (_, index) {
            return code[Number(index)];
        });
        return text;
    }

    function isTableSeparator(line) {
        var cells = line.trim().replace(/^\|/, "").replace(/\|$/, "").split("|");
        return cells.length > 0 && cells.every(function (cell) {
            return /^\s*:?-{3,}:?\s*$/.test(cell);
        });
    }

    function splitTableRow(line) {
        var value = line.trim();
        if (value.charAt(0) === "|") value = value.slice(1);
        if (value.charAt(value.length - 1) === "|") value = value.slice(0, -1);
        return value.split("|").map(function (cell) { return cell.trim(); });
    }

    function renderTable(lines) {
        var headers = splitTableRow(lines[0]);
        var html = "<div class=\"markdown-table-wrap\"><table><thead><tr>";
        headers.forEach(function (header) {
            html += "<th>" + inlineMarkdown(header) + "</th>";
        });
        html += "</tr></thead><tbody>";
        for (var i = 2; i < lines.length; i += 1) {
            var cells = splitTableRow(lines[i]);
            html += "<tr>";
            for (var j = 0; j < headers.length; j += 1) {
                html += "<td>" + inlineMarkdown(cells[j] || "") + "</td>";
            }
            html += "</tr>";
        }
        return html + "</tbody></table></div>";
    }

    function renderMarkdown(markdown) {
        var source = String(markdown == null ? "" : markdown).replace(/\r\n?/g, "\n");
        var lines = source.split("\n");
        var html = [];
        var paragraph = [];
        var listType = null;
        var listItems = [];
        var inCode = false;
        var codeLanguage = "";
        var codeLines = [];

        function flushParagraph() {
            if (paragraph.length) {
                html.push("<p>" + paragraph.map(inlineMarkdown).join("<br>") + "</p>");
                paragraph = [];
            }
        }

        function flushList() {
            if (!listItems.length) return;
            html.push("<" + listType + ">" + listItems.map(function (item) {
                return "<li>" + inlineMarkdown(item) + "</li>";
            }).join("") + "</" + listType + ">");
            listType = null;
            listItems = [];
        }

        function flushCode() {
            var className = codeLanguage ? " class=\"language-" + escapeHtml(codeLanguage) + "\"" : "";
            html.push("<pre><code" + className + ">" + escapeHtml(codeLines.join("\n")) + "</code></pre>");
            codeLines = [];
            codeLanguage = "";
        }

        for (var i = 0; i < lines.length; i += 1) {
            var line = lines[i];
            var fence = line.match(/^\s*```\s*([\w-]*)\s*$/);
            if (fence) {
                if (inCode) {
                    flushCode();
                    inCode = false;
                } else {
                    flushParagraph();
                    flushList();
                    inCode = true;
                    codeLanguage = fence[1];
                }
                continue;
            }
            if (inCode) {
                codeLines.push(line);
                continue;
            }

            if (line.trim() === "") {
                flushParagraph();
                flushList();
                continue;
            }

            if (i + 1 < lines.length && /^\s*\|?.+\|.+\|?\s*$/.test(line) && isTableSeparator(lines[i + 1])) {
                flushParagraph();
                flushList();
                var tableLines = [line, lines[i + 1]];
                i += 2;
                while (i < lines.length && lines[i].trim() !== "" && /^\s*\|?.+\|.+\|?\s*$/.test(lines[i])) {
                    tableLines.push(lines[i]);
                    i += 1;
                }
                i -= 1;
                html.push(renderTable(tableLines));
                continue;
            }

            var heading = line.match(/^\s*(#{1,6})\s+(.+?)\s*#*\s*$/);
            if (heading) {
                flushParagraph();
                flushList();
                html.push("<h" + heading[1].length + ">" + inlineMarkdown(heading[2]) + "</h" + heading[1].length + ">");
                continue;
            }

            var quote = line.match(/^\s*>\s?(.*)$/);
            if (quote) {
                flushParagraph();
                flushList();
                html.push("<blockquote>" + inlineMarkdown(quote[1]) + "</blockquote>");
                continue;
            }

            var list = line.match(/^\s*([-*+] |\d+[.)] )(.*)$/);
            if (list) {
                flushParagraph();
                var nextType = /^\d/.test(list[1]) ? "ol" : "ul";
                if (listType && listType !== nextType) flushList();
                listType = listType || nextType;
                listItems.push(list[2]);
                continue;
            }

            if (/^\s*([-*_])\s*\1\s*\1(?:\s*\1)*\s*$/.test(line)) {
                flushParagraph();
                flushList();
                html.push("<hr>");
                continue;
            }

            flushList();
            paragraph.push(line);
        }

        if (inCode) flushCode();
        flushParagraph();
        flushList();
        return html.join("");
    }

    window.escapeHtml = escapeHtml;
    window.renderMarkdown = renderMarkdown;
}());
