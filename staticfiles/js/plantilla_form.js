// plantilla_form.js — Validación de JSON + miniatura (sin inline CSP)
(function () {
  function $(id) { return document.getElementById(id); }

  document.addEventListener("DOMContentLoaded", function () {
    var ta   = $("json");
    var badge= $("jsonBadge");
    var form = $("tplForm");
    var btnExample = $("btnExample");
    var cvs = $("thumb");
    var ctx = cvs.getContext("2d");

    function setBadge(ok, msgOK, msgBad){
      if(ok){
        badge.className = "pill ok";
        badge.textContent = msgOK || "JSON válido";
      }else{
        badge.className = "pill bad";
        badge.textContent = msgBad || "JSON inválido";
      }
    }

    function validate(){
      try{
        var obj = JSON.parse(ta.value);
        if(!obj.pages || !obj.pages.length){
          setBadge(false, null, 'Faltan "pages"');
          return null;
        }
        setBadge(true);
        return obj;
      }catch(e){
        setBadge(false, null, "Error de sintaxis");
        return null;
      }
    }

    function drawThumb(){
      var data = validate();
      ctx.clearRect(0,0,cvs.width,cvs.height);
      if(!data) return;

      var p = data.pages[0] || {};
      var W = p.width || 800, H = p.height || 600;
      var scale = Math.min(cvs.width/W, cvs.height/H);

      // Fondo del lienzo
      ctx.fillStyle = p.background || "#ffffff";
      var w=W*scale, h=H*scale, x=(cvs.width-w)/2, y=(cvs.height-h)/2;
      ctx.fillRect(x,y,w,h);
      ctx.strokeStyle = "#cbd5e1";
      ctx.strokeRect(x,y,w,h);

      // Capas (boceto)
      (p.layers||[]).forEach(function(l){
        ctx.save();
        if(l.type==="rect"){
          ctx.fillStyle=l.fill||"#ddd";
          ctx.fillRect(x+l.x*scale, y+l.y*scale, (l.w||100)*scale, (l.h||60)*scale);
        }
        if(l.type==="text"){
          ctx.fillStyle=l.fill||"#111";
          ctx.font = ((l.fontSize||24)*scale) + "px sans-serif";
          ctx.fillText("T", x+l.x*scale, y+l.y*scale);
        }
        if(l.type==="circle"){
          ctx.fillStyle=l.fill||"#ddd";
          ctx.beginPath();
          ctx.arc(x+l.x*scale, y+l.y*scale, (l.r||40)*scale, 0, Math.PI*2);
          ctx.fill();
        }
        if(l.type==="line"){
          ctx.strokeStyle=l.stroke||"#111";
          ctx.lineWidth=(l.strokeWidth||2)*scale;
          ctx.beginPath();
          ctx.moveTo(x+(l.x||0)*scale, y+(l.y||0)*scale);
          ctx.lineTo(x+(l.x2||100)*scale, y+(l.y2||0)*scale);
          ctx.stroke();
        }
        if(l.type==="image"){
          ctx.fillStyle="#e5e7eb";
          ctx.fillRect(x+l.x*scale, y+l.y*scale, (l.w||120)*scale, (l.h||80)*scale);
          ctx.fillStyle="#94a3b8";
          ctx.fillText("img", x+l.x*scale+6, y+l.y*scale+14);
        }
        ctx.restore();
      });
    }

    ta.addEventListener("input", function(){ validate(); drawThumb(); });
    validate(); drawThumb();

    if(btnExample){
      btnExample.addEventListener("click", function(){
        // Nota: como este archivo es estático, las llaves dobles quedan literales.
        ta.value = [
          "{",
          '  "pages":[{ "width":1280, "height":720, "background":"#ffffff",',
          '    "layers":[',
          '      { "id":"l1", "type":"text", "text":"{{ nombre }}", "x":72, "y":180, "fontSize":48, "fill":"#111111" },',
          '      { "id":"l2", "type":"text", "text":"Diplomado en {{ programa }}", "x":72, "y":250, "fontSize":28, "fill":"#4b5563" },',
          '      { "id":"l3", "type":"rect", "x":64, "y":420, "w":1152, "h":3, "fill":"#e5e7eb" },',
          '      { "id":"l4", "type":"image", "url":"{{ qr_url }}", "x":1040, "y":520, "w":160, "h":160 }',
          "    ]",
          "  }]}",
        ].join("\n");
        ta.dispatchEvent(new Event("input"));
      });
    }

    form.addEventListener("submit", function(e){
      if(!validate()){
        e.preventDefault();
        alert("Corrige el JSON antes de continuar.");
      }
    });
  });
})();
