/* Six original procedural scenes. All motion is drawn locally; no remote assets. */
class SceneEngine {
  constructor(canvas) {
    this.canvas=canvas;this.ctx=canvas.getContext('2d',{alpha:false});
    const random=i=>{let x=Math.sin(i*127.1+311.7)*43758.5453;return x-Math.floor(x);};
    this.p=Array.from({length:500},(_,i)=>({x:random(i*7),y:random(i*7+1),z:random(i*7+2),r:random(i*7+3),a:random(i*7+4),v:random(i*7+5),phase:random(i*7+6)*Math.PI*2}));
    this.resize=()=>{this.w=innerWidth;this.h=innerHeight;const d=Math.min(devicePixelRatio||1,1.75);canvas.width=Math.round(this.w*d);canvas.height=Math.round(this.h*d);this.ctx.setTransform(d,0,0,d,0,0);};
    addEventListener('resize',this.resize);this.resize();
  }
  rgba(hex,a){const n=parseInt(hex.slice(1),16);return `rgba(${n>>16},${n>>8&255},${n&255},${Math.max(0,Math.min(1,a))})`;}
  base(top,bottom){const c=this.ctx,g=c.createLinearGradient(0,0,0,this.h);g.addColorStop(0,top);g.addColorStop(1,bottom);c.fillStyle=g;c.fillRect(0,0,this.w,this.h);}
  glow(x,y,r,color,alpha=1){if(r<=0)return;const c=this.ctx,g=c.createRadialGradient(x,y,0,x,y,r);g.addColorStop(0,this.rgba(color,alpha));g.addColorStop(.35,this.rgba(color,alpha*.35));g.addColorStop(1,this.rgba(color,0));c.fillStyle=g;c.fillRect(x-r,y-r,r*2,r*2);}
  dot(x,y,r,color,a=1){const c=this.ctx;c.fillStyle=this.rgba(color,a);c.beginPath();c.arc(x,y,Math.max(.1,r),0,Math.PI*2);c.fill();}
  line(points,color,width=1,a=1){const c=this.ctx;c.strokeStyle=this.rgba(color,a);c.lineWidth=width;c.beginPath();points.forEach((p,i)=>c[i?'lineTo':'moveTo'](...p));c.stroke();}
  stars(t,count=180,color='#d5e9ff',speed=1){const {w,h}=this;for(let i=0;i<count;i++){const p=this.p[i],x=(p.x*w+Math.sin(t*.025+p.phase)*10+w)%w,y=((p.y-t*.001*speed*(.2+p.z))*h%h+h)%h;this.dot(x,y,.3+p.r*1.2,color,(.25+p.a*.65)*(.75+.25*Math.sin(t+p.phase)));}}
  render(theme,t,a){this.frameCount=(this.frameCount||0)+1;this.time=t;const c=this.ctx;c.save();c.globalCompositeOperation='source-over';c.globalAlpha=1;this[theme](t,a);c.restore();}
  galaxy(t,a){
    const {ctx:c,w,h}=this;this.base('#030513','#09091c');
    c.save();c.globalCompositeOperation='screen';
    for(let i=0;i<14;i++){let phase=i*.7+t*.045,x=w*.48+Math.cos(phase)*w*(.18+i*.012),y=h*.60+Math.sin(phase*.7)*h*.19;this.glow(x,y,w*(.28+a.bass*.06),i%3?'#6647ad':'#145f94',.12+a.level*.08);}
    c.restore();this.stars(t,Math.round(a.density*1.1));
    // Curved dust lanes sweep through the nebula, changing depth with the beat.
    c.save();c.translate(w*.51,h*.63);c.rotate(-.65+Math.sin(t*.035)*.1);c.scale(1,.36);
    for(let i=0;i<a.density;i++){const p=this.p[i],ang=p.x*Math.PI*2+t*(.025+p.z*.012),radius=w*(.15+p.z*.7)*(1+a.beat*.025);this.dot(Math.cos(ang)*radius,Math.sin(ang)*radius, .5+p.r*1.5,i%4?'#c5a5f4':'#6deaff',(.15+p.a*.45)*(1-p.z*.5));}
    c.restore();
    // A real planet, with a shaded night side and a thin illuminated atmosphere.
    const px=w*.76+Math.sin(t*.025)*w*.025,py=h*.64+Math.cos(t*.03)*h*.015,r=w*.245;
    this.glow(px-r*.2,py-r*.3,r*1.5,'#8c70ef',.23+a.level*.15);
    const g=c.createRadialGradient(px-r*.45,py-r*.5,r*.02,px,py,r);g.addColorStop(0,'#7a70ab');g.addColorStop(.24,'#35365e');g.addColorStop(.7,'#101225');g.addColorStop(1,'#02040c');c.fillStyle=g;c.beginPath();c.arc(px,py,r,0,Math.PI*2);c.fill();
    c.save();c.beginPath();c.arc(px,py,r,0,Math.PI*2);c.clip();
    for(let i=0;i<8;i++){const y=py-r+i*r*.24;this.line([[px-r,y],[px-r*.2,y+r*.05*Math.sin(t*.07+i)],[px+r,y-r*.1]],'#8286bf',r*.025,.06);}
    c.restore();c.strokeStyle='#b6a7ff70';c.lineWidth=1.2;c.beginPath();c.arc(px,py,r,-Math.PI*.96,-Math.PI*.13);c.stroke();
    // Meteors move independently of the star field.
    for(let i=0;i<3;i++){const cycle=(t*.11+i*.37)%1;if(cycle<.18){const q=cycle/.18,x=w*(.05+i*.27)+q*w*.6,y=h*(.08+i*.16)+q*h*.23;const grad=c.createLinearGradient(x-60,y-40,x,y);grad.addColorStop(0,'#9aeaff00');grad.addColorStop(1,'#e8f3ffdd');c.strokeStyle=grad;c.lineWidth=1;c.beginPath();c.moveTo(x-60,y-40);c.lineTo(x,y);c.stroke();this.dot(x,y,1.1,'#eff9ff',1-q);}}
    this.glow(w*.05,h*.95,w*.8,'#215eb7',.13);
  }
  city(t,a){
    const {ctx:c,w,h}=this,hy=h*.56,vx=w*.52;this.base('#020912','#111429');
    this.glow(vx,hy,w*.7,'#487087',.27+a.level*.12);this.glow(w*.12,h*.6,w*.5,'#ed3f91',.17);this.glow(w*.85,h*.4,w*.6,'#22a7c0',.16);
    // Distant city layers.
    for(let layer=0;layer<3;layer++){for(let i=0;i<17;i++){const p=this.p[100+layer*20+i],bw=w*(.035+layer*.012),x=i*w/16-bw/2,roof=hy-h*(.035+p.y*(.1+layer*.055));c.fillStyle=['#111d2d','#0b1522','#060e19'][layer];c.fillRect(x,roof,bw,hy-roof);for(let j=0;j<7;j++){if((i+j+layer)%3){c.fillStyle=this.rgba(j%2?'#68d9e5':'#a369bb',.12+p.a*.22+a.beat*.15);c.fillRect(x+bw*.25,roof+8+j*10,2,3);}}}}
    // Foreground towers frame a wet street, rather than an audio spectrum.
    for(const side of [-1,1]){for(let i=0;i<5;i++){const p=this.p[200+i+(side+1)*5],bw=w*(.12+p.x*.09),x=side<0?-w*.03+i*w*.055:w*.86-i*w*.055,roof=h*(.12+i*.07+p.y*.08),bottom=h;c.fillStyle=i%2?'#070e19':'#09111d';c.fillRect(x,roof,bw,bottom-roof);c.strokeStyle=this.rgba(side<0?'#c44691':'#4db5c6',.14);c.strokeRect(x,roof,bw,bottom-roof);
      for(let row=0;row<18;row++)for(let col=0;col<3;col++){const on=this.p[(row*3+col+i*7)%500].a>.43;if(on){c.fillStyle=this.rgba(side<0?'#f5b17d':'#8de7f6',.12+this.p[row+col].r*.2+a.beat*.1);c.fillRect(x+bw*(.17+col*.27),roof+14+row*15,3,6);}}
      if(i%2===0){const sx=side<0?x+bw-4:x+3,sy=roof+30;c.shadowColor=side<0?'#ff4fa2':'#56edff';c.shadowBlur=15;c.fillStyle=side<0?'#ff66b1':'#78e7f7';c.fillRect(sx,sy,3,45+i*5);c.shadowBlur=0;}
    }}
    // Street perspective and moving light reflections on the rain-soaked asphalt.
    const road=c.createLinearGradient(0,hy,0,h);road.addColorStop(0,'#0a1624');road.addColorStop(1,'#050911');c.fillStyle=road;c.beginPath();c.moveTo(vx-w*.025,hy);c.lineTo(vx+w*.025,hy);c.lineTo(w*.98,h);c.lineTo(w*.02,h);c.closePath();c.fill();
    for(let i=0;i<70;i++){const p=this.p[i],depth=((p.y+t*.018*(.3+p.v))%1),yy=hy+depth*depth*(h-hy),xx=vx+(p.x-.5)*w*(.12+depth),len=(3+p.r*24)*depth;c.fillStyle=this.rgba(i%2?'#f74a9d':'#4ac1e0',(.08+p.a*.2)*depth*(1+a.level));c.fillRect(xx-len/2,yy,len,Math.max(.5,depth*2));}
    this.line([[vx-8,hy],[w*.17,h]],'#557a92',1,.18);this.line([[vx+8,hy],[w*.83,h]],'#557a92',1,.18);
    this.glow(vx,hy+8,w*.15,'#f098a9',.32+a.bass*.22);
    // Rain streaks traverse the full scene at several apparent depths.
    for(let i=0;i<a.density;i++){const p=this.p[i],x=((p.x-t*.025*(.5+p.z))*w%w+w)%w,y=((p.y+t*(.24+p.z*.24))*h)%h;this.line([[x,y],[x-3-p.z*4,y+9+p.z*22]],i%4?'#82b7ce':'#f19abb',.4+p.z*.7,.08+p.a*.23);}
    for(let i=0;i<12;i++){const p=this.p[300+i],q=(t*.5+p.y)%1;c.strokeStyle=this.rgba('#a7cada',(1-q)*.11);c.beginPath();c.ellipse(p.x*w,h*(.77+p.z*.22),q*12,q*3,0,0,Math.PI*2);c.stroke();}
  }
  ember(t,a){
    const {ctx:c,w,h}=this;this.base('#0e070a','#270e09');this.glow(w*.5,h*.76,w*.9,'#e74514',.42+a.bass*.18);this.glow(w*.5,h*.52,w*.5,'#f19338',.16);
    // Layers of drifting volcanic smoke.
    for(let i=0;i<14;i++){const p=this.p[i],x=w*(p.x+.09*Math.sin(t*.08+p.phase)),y=((p.y-t*.015)%1+1)%1*h;this.glow(x,y,w*(.35+p.r*.25),i%2?'#7d2517':'#ac4924',.065+a.level*.025);}
    // Obsidian banks frame a flowing river of lava.
    c.fillStyle='#07070b';for(const side of [-1,1]){c.beginPath();c.moveTo(side<0?0:w,h*.48);for(let j=0;j<10;j++){let y=h*(.48+j*.06),edge=w*.5+side*w*(.04+j*.037+.035*Math.sin(j*2.2));c.lineTo(edge,y);}c.lineTo(side<0?0:w,h);c.closePath();c.fill();}
    c.save();c.globalCompositeOperation='screen';
    for(let layer=0;layer<5;layer++){const width=layer===0?26:10-layer*.9;const pts=[];for(let j=0;j<=60;j++){const d=j/60,y=h*(.54+d*.5),x=w*.5+Math.sin(d*6-t*.12)*w*.09*d+Math.sin(d*15+t*.2)*w*.015*d;pts.push([x,y]);}c.lineCap='round';const gradient=c.createLinearGradient(0,h*.5,0,h);gradient.addColorStop(0,this.rgba('#fb561c',.15));gradient.addColorStop(.5,this.rgba(layer%2?'#ff8d25':'#fd4c10',.45));gradient.addColorStop(1,this.rgba(layer%2?'#ffc37b':'#f34c14',.7));c.strokeStyle=gradient;c.lineWidth=width*w/300;c.shadowColor='#ff571b';c.shadowBlur=20+layer*9;c.beginPath();pts.forEach((p,i)=>c[i?'lineTo':'moveTo'](p[0]+Math.sin(i*.25+layer)*layer*3,p[1]));c.stroke();}
    c.restore();
    // Flame tongues curl above the glowing river and respond to bass pulses.
    for(let i=0;i<13;i++){const p=this.p[50+i],x=w*(.3+p.x*.4),bottom=h*(.9+p.y*.15),height=h*(.08+p.r*.12)*(1+a.bass*.5);const g=c.createLinearGradient(x,bottom-height,x,bottom);g.addColorStop(0,'#ffb25500');g.addColorStop(.7,'#f8651c14');g.addColorStop(1,'#ffb45555');c.fillStyle=g;c.beginPath();c.moveTo(x-12,bottom);c.bezierCurveTo(x+28*Math.sin(t+p.phase),bottom-height*.5,x-25, bottom-height*.7,x+Math.sin(t*1.3+p.phase)*15,bottom-height);c.bezierCurveTo(x+5,bottom-height*.6,x+16,bottom-height*.2,x+12,bottom);c.fill();}
    for(let i=0;i<a.density;i++){const p=this.p[i],q=(p.y+t*(.035+p.v*.055)*(1+a.level*.6))%1,y=h*(1.1-q*1.25),x=p.x*w+Math.sin(t*.4+p.phase+q*8)*w*.035;this.line([[x,y],[x-1,y+4+p.z*12]],'#ff9f42',.5+p.z,.12+p.a*.32);this.dot(x,y,.5+p.r*1.6,'#ffd29a',(.25+p.a*.7)*Math.sin(q*Math.PI));if(i%22===0)this.glow(x,y,14,'#ff7032',.17);}
    this.glow(w*.5,h*1.05,w*.9,'#ff742c',.3+a.beat*.2);
  }
  aurora(t,a){
    const {ctx:c,w,h}=this;this.base('#030f1c','#133742');this.glow(w*.5,h*.47,w,'#1c5c66',.12);this.stars(t,Math.round(a.density*.7),'#d2f9f5',.15);
    // Light curtains consist of many filaments, with individual flowing heights.
    c.save();c.globalCompositeOperation='screen';
    for(let layer=0;layer<3;layer++){const count=110;for(let i=0;i<count;i++){const q=i/(count-1),x=q*w*1.35-w*.15,base=h*(.35+layer*.08)+Math.sin(q*5.2+t*.17+layer*.7)*h*.12+Math.sin(q*12-t*.2)*h*.025,stretch=h*(.13+.075*Math.sin(q*8+t*.3+layer))*(1+a.level*.25),bend=Math.sin(q*7+t*.25)*w*.08;const color=layer===1?'#a98fe9':layer===2?'#73dfc2':'#82f7bd',g=c.createLinearGradient(x,base-stretch,x,base+18);g.addColorStop(0,this.rgba(color,0));g.addColorStop(.5,this.rgba(color,.035+a.bass*.025));g.addColorStop(.91,this.rgba(color,.17+a.level*.08));g.addColorStop(1,this.rgba(color,0));c.strokeStyle=g;c.lineWidth=w/count*1.9;c.beginPath();c.moveTo(x+bend,base-stretch);c.bezierCurveTo(x+bend*.7,base-stretch*.6,x,base-stretch*.1,x,base+18);c.stroke();}}
    c.restore();
    // A cold moon and its atmospheric halo.
    this.glow(w*.8,h*.16,w*.16,'#d3eee9',.17);this.dot(w*.8,h*.16,w*.031,'#e1eeea',.85);
    const layers=[{y:.78,color:'#19313e',peaks:[.06,.16,-.03,.21,.05,.14,-.01,.19,.06,.11]}, {y:.9,color:'#0d202d',peaks:[.02,.16,.08,.23,.05,.18,.1,.29,.12,.02]}, {y:1.03,color:'#07131e',peaks:[.05,.1,.02,.12,.07,.17,.04,.08,.03,.1]}];
    for(const [index,layer] of layers.entries()){c.fillStyle=layer.color;c.beginPath();c.moveTo(-30,h);for(let i=0;i<layer.peaks.length;i++)c.lineTo(i*w/(layer.peaks.length-1),h*(layer.y-layer.peaks[i]));c.lineTo(w+30,h);c.closePath();c.fill();if(index===0){for(let i=1;i<9;i+=2){const x=i*w/9,y=h*(layer.y-layer.peaks[i]);c.fillStyle='#7aabae55';c.beginPath();c.moveTo(x,y);c.lineTo(x-12,y+27);c.lineTo(x,y+19);c.lineTo(x+10,y+32);c.closePath();c.fill();}}}
    // Snow motes move slowly in front of the landscape.
    for(let i=0;i<Math.round(a.density*.45);i++){const p=this.p[220+i],x=(p.x*w+Math.sin(t*.1+p.phase)*15+w)%w,y=((p.y+t*.013*(.4+p.z))*h)%h;this.dot(x,y,.35+p.r,'#d7f4f3',.13+p.a*.36);}
  }
  abyss(t,a){
    const {ctx:c,w,h}=this;this.base('#07313b','#020b1b');this.glow(w*.6,-h*.1,w*.9,'#42b5b9',.28);this.glow(w*.15,h*.75,w*.6,'#235c8f',.22);
    // Shafts of light refract through a slowly moving water surface.
    c.save();c.globalCompositeOperation='screen';for(let i=0;i<7;i++){const x=w*(i/6)+Math.sin(t*.06+i)*w*.1,g=c.createLinearGradient(x,0,x,h*.75);g.addColorStop(0,'#77e2d81c');g.addColorStop(1,'#77e2d800');c.fillStyle=g;c.beginPath();c.moveTo(x-5,0);c.lineTo(x+7,0);c.lineTo(x+w*.22,h*.8);c.lineTo(x-w*.14,h*.8);c.closePath();c.fill();}c.restore();
    for(let i=0;i<a.density;i++){const p=this.p[i],x=(p.x*w+Math.sin(t*.12+p.phase)*12+w)%w,y=((p.y-t*.009*(.5+p.z))*h%h+h)%h;this.dot(x,y,.25+p.r*1.1,i%3?'#8debd9':'#8b9af8',(.1+p.a*.45)*(.6+a.high*.8));}
    const jelly=(x,y,size,phase,alpha)=>{const pulse=1+Math.sin(t*1.1+phase)*.055+a.bass*.07;c.save();c.translate(x,y);c.scale(pulse,pulse);c.globalAlpha=alpha;
      this.glow(0,-size*.12,size*1.6,'#5dcedb',.12+a.level*.12);
      // Long independent tentacles, rather than rigid spectrum bars.
      for(let j=0;j<11;j++){const offset=(j/10-.5)*size*1.4,len=size*(1.8+this.p[j+40].z*2.1),pts=[];for(let k=0;k<30;k++){const q=k/29;pts.push([offset+Math.sin(t*.85+q*5+phase+j*.43)*q*size*.3, q*len]);}const g=c.createLinearGradient(0,0,0,len);g.addColorStop(0,'#a2c8f06b');g.addColorStop(.45,'#7bceea44');g.addColorStop(1,'#6288e900');c.strokeStyle=g;c.lineWidth=j%2?.7:1.2;c.beginPath();pts.forEach((p,i)=>c[i?'lineTo':'moveTo'](...p));c.stroke();}
      const dome=c.createRadialGradient(-size*.25,-size*.5,0,0,-size*.1,size);dome.addColorStop(0,'#c5f7f58a');dome.addColorStop(.5,'#51a5cc28');dome.addColorStop(1,'#9bd6ef99');c.fillStyle=dome;c.beginPath();c.moveTo(-size,0);c.bezierCurveTo(-size,-size*1.23,size,-size*1.23,size,0);c.quadraticCurveTo(size*.5,-size*.13,0,size*.05);c.quadraticCurveTo(-size*.5,-size*.13,-size,0);c.fill();c.strokeStyle='#a4f7f699';c.lineWidth=1;c.stroke();
      for(let j=0;j<6;j++){c.strokeStyle='#a6def133';c.lineWidth=.6;c.beginPath();c.moveTo(0,-size*.9);c.quadraticCurveTo((j/5-.5)*size*.8,-size*.65,(j/5-.5)*size*1.65,0);c.stroke();}this.glow(0,-size*.15,size*.5,'#a2beff',.17+a.beat*.25);c.restore();};
    jelly(w*.2+Math.sin(t*.12)*w*.06,h*.56+Math.sin(t*.19)*h*.025,w*.083,1,.5);
    jelly(w*.77+Math.sin(t*.08+1)*w*.045,h*.48+Math.sin(t*.14+1)*h*.03,w*.06,3,.35);
    jelly(w*.58+Math.sin(t*.1)*w*.07,h*.69+Math.sin(t*.16)*h*.035,w*.185,0,.85);
    jelly(w*.15+Math.sin(t*.09+3)*w*.06,h*.93+Math.sin(t*.13+3)*h*.03,w*.11,2,.55);
    for(let i=0;i<18;i++){const p=this.p[350+i],y=((p.y-t*.024)%1+1)%1*h,x=p.x*w+Math.sin(t*.4+p.phase)*7;c.strokeStyle=this.rgba('#a1e8e9',.06+p.a*.13);c.lineWidth=.6;c.beginPath();c.arc(x,y,1+p.r*3,0,Math.PI*2);c.stroke();}
  }
  gold(t,a){
    const {ctx:c,w,h}=this;this.base('#0e0d0b','#21190e');this.glow(w*.9,h*.2,w*.9,'#9d6933',.19);this.glow(w*.15,h*.85,w*.7,'#b98134',.17);
    // Broad metallic ribbons flow through the scene with bright folded edges.
    for(let layer=0;layer<9;layer++){const points=[],base=h*(.42+layer*.062);for(let i=0;i<=70;i++){const q=i/70,x=q*w*1.5-w*.25,y=base+Math.sin(q*5+t*.12+layer*.4)*h*.12+Math.sin(q*10-t*.1+layer*.2)*h*.035*(1+a.bass*.3);points.push([x,y]);}
      c.save();c.lineCap='round';const thickness=w*(.045+layer*.004),g=c.createLinearGradient(0,base-h*.12,w,base+h*.12);g.addColorStop(0,'#392718');g.addColorStop(.18,'#a67c42');g.addColorStop(.32,'#f5d99b');g.addColorStop(.38,'#fff0c9');g.addColorStop(.48,'#9b7037');g.addColorStop(.62,'#281c11');g.addColorStop(.8,'#ccaa67');g.addColorStop(1,'#594020');c.strokeStyle=g;c.lineWidth=thickness;c.globalAlpha=.35+layer*.045;c.shadowBlur=16;c.shadowColor='#000000';c.beginPath();points.forEach((p,i)=>c[i?'lineTo':'moveTo'](...p));c.stroke();c.shadowBlur=0;c.lineWidth=.8;c.strokeStyle=this.rgba('#ffe9b7',.17+a.level*.19);c.beginPath();points.forEach((p,i)=>c[i?'lineTo':'moveTo'](p[0],p[1]-thickness*.47));c.stroke();c.restore();}
    // Metallic droplets drift in the foreground and catch animated specular light.
    for(let i=0;i<10;i++){const p=this.p[180+i],x=p.x*w+Math.sin(t*.09+p.phase)*w*.04,y=((p.y-t*.008*(.5+p.v))%1+1)%1*h,r=w*(.008+p.r*.024)*(1+a.beat*.04);const g=c.createRadialGradient(x-r*.35,y-r*.45,r*.03,x,y,r);g.addColorStop(0,'#fff4cd');g.addColorStop(.13,'#eed395');g.addColorStop(.35,'#8f6838');g.addColorStop(.55,'#251b11');g.addColorStop(.8,'#b38947');g.addColorStop(1,'#4e371c');c.fillStyle=g;c.beginPath();c.arc(x,y,r,0,Math.PI*2);c.fill();}
    for(let i=0;i<Math.round(a.density*.6);i++){const p=this.p[i],x=(p.x*w+Math.sin(t*.05+p.phase)*10+w)%w,y=((p.y-t*.009*(.4+p.z))%1+1)%1*h;this.dot(x,y,.25+p.r*.9,'#f3dda9',(.13+p.a*.45)*(.7+a.level*.5));if(i%33===0){const twinkle=Math.pow(Math.max(0,Math.sin(t*.7+p.phase)),8);this.line([[x-5,y],[x+5,y]],'#ffebbb',.6,twinkle*.5);this.line([[x,y-5],[x,y+5]],'#ffebbb',.6,twinkle*.5);}}
    this.glow(w*.8,h*.82,w*.42,'#f9db8c',.035+a.beat*.075);
  }
}
