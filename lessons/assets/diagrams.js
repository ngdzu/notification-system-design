/* diagrams.js — reusable SVG diagram components for the notification course.
   Loaded by lesson HTML via <script defer src="../assets/diagrams.js"></script>.
   Components render inline SVG into light DOM, so all classes/animations come
   from course.css. Promote a new diagram archetype here only once 2+ lessons
   need it; one-off diagrams stay hand-written in their lesson file.

   <nc-actors mode="push|poll|hybrid" label="..." label2="...">
     Server-to-client actor lane with animated message dots.
     mode=push   solid wire, streaming dots, ringing client
     mode=poll   dashed wires, request/response dots on a schedule
     mode=hybrid amber push wire over a cyan poll wire
     label / label2 override the wire captions (label2: hybrid's lower wire). */

(function () {
  "use strict";

  function esc(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  function serverBox(stripes) {
    var ys = [25, 32, 39], ops = [0.9, 0.55, 0.3], out = '<rect class="box" x="8" y="18" width="46" height="40" rx="4"/>';
    for (var i = 0; i < 3; i++) {
      out += '<rect x="14" y="' + ys[i] + '" width="34" height="3" rx="1.5" fill="var(--' + stripes[i] + ')" opacity="' + ops[i] + '"/>';
    }
    return out + '<text class="lbl" x="31" y="70" text-anchor="middle">server</text>';
  }

  function clientBox(inner) {
    return '<rect class="box" x="188" y="14" width="30" height="50" rx="6"/>' + inner +
      '<text class="lbl" x="203" y="76" text-anchor="middle">client</text>';
  }

  var DEFAULTS = {
    push: { label: "always-open connection" },
    poll: { label: "“anything new?” — every 30 s" },
    hybrid: { label: "push = fast path", label2: "pull = safety net (catch-up)" }
  };

  var ARIA = {
    push: "Server pushes messages instantly to a client over an always-open connection",
    poll: "Client polls the server on a schedule; a reply comes back only when asked",
    hybrid: "Push is the fast path; pull runs underneath as the safety net"
  };

  var MODES = {
    push: function (o) {
      return serverBox(["amber", "amber", "amber"]) +
        '<line class="wire a-stroke" x1="54" y1="38" x2="186" y2="38" opacity="0.45"/>' +
        '<text class="lbl a-text" x="120" y="30" text-anchor="middle" style="font-size:8px">' + esc(o.label) + "</text>" +
        '<g><circle class="a-fill push-dot" cx="60" cy="38" r="4"/></g>' +
        '<g><circle class="a-fill push-dot d2" cx="60" cy="38" r="4"/></g>' +
        clientBox('<circle class="push-ring" cx="203" cy="39" r="9" fill="none" stroke="var(--amber)" stroke-width="2"/>' +
          '<circle class="a-fill" cx="203" cy="39" r="3.5"/>');
    },
    poll: function (o) {
      return serverBox(["cyan", "cyan", "cyan"]) +
        '<line class="wire" x1="54" y1="30" x2="186" y2="30" stroke-dasharray="3 4"/>' +
        '<line class="wire" x1="54" y1="48" x2="186" y2="48" stroke-dasharray="3 4"/>' +
        '<text class="lbl c-text" x="120" y="24" text-anchor="middle" style="font-size:8px">' + esc(o.label) + "</text>" +
        '<g><circle class="poll-req" cx="180" cy="30" r="4" fill="none" stroke="var(--cyan)" stroke-width="2"/></g>' +
        '<g><circle class="c-fill poll-resp" cx="60" cy="48" r="4"/></g>' +
        clientBox('<circle class="c-fill blink" cx="203" cy="39" r="3.5"/>');
    },
    hybrid: function (o) {
      return serverBox(["amber", "cyan", "amber"]) +
        '<line class="wire a-stroke" x1="54" y1="30" x2="186" y2="30" opacity="0.5"/>' +
        '<text class="lbl a-text" x="120" y="24" text-anchor="middle" style="font-size:8px">' + esc(o.label) + "</text>" +
        '<g><circle class="a-fill push-dot" cx="60" cy="30" r="4"/></g>' +
        '<line class="wire c-stroke" x1="54" y1="52" x2="186" y2="52" stroke-dasharray="3 4" opacity="0.6"/>' +
        '<text class="lbl c-text" x="120" y="64" text-anchor="middle" style="font-size:8px">' + esc(o.label2) + "</text>" +
        '<g><circle class="poll-req" cx="180" cy="52" r="3.5" fill="none" stroke="var(--cyan)" stroke-width="2"/></g>' +
        clientBox('<circle class="a-fill" cx="203" cy="33" r="3"/><circle class="c-fill blink" cx="203" cy="46" r="3"/>');
    }
  };

  class NcActors extends HTMLElement {
    connectedCallback() {
      var mode = this.getAttribute("mode") || "push";
      if (!MODES[mode]) mode = "push";
      var opts = {
        label: this.getAttribute("label") || DEFAULTS[mode].label,
        label2: this.getAttribute("label2") || DEFAULTS[mode].label2 || ""
      };
      this.innerHTML =
        '<svg viewBox="0 0 240 80" role="img" aria-label="' + esc(this.getAttribute("aria-label") || ARIA[mode]) + '">' +
        MODES[mode](opts) + "</svg>";
    }
  }
  customElements.define("nc-actors", NcActors);
})();
