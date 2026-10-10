'use strict';

/**
 * OPORTUNIDADES (edite este arquivo para atualizar a página de oportunidades)
 *
 * Cada oportunidade é um bloco { ... } dentro da sua categoria. Campos:
 *   tipo      : rótulo curto do card (ex.: "Bolsa", "Cursinho", "Estágio")
 *   titulo    : nome da oportunidade
 *   descricao : 1 ou 2 frases explicando para quem é e como participar
 *   local     : selo no canto da imagem (ex.: "Online", "São Paulo", "Todo o Brasil")
 *   link      : endereço oficial (inscrição ou mais informações)
 *   imagem    : imagem do card (pasta assets/images)
 *
 * Datas, vagas e regras mudam com frequência: confira sempre o site oficial antes de divulgar.
 */

window.OPORTUNIDADES = {

  categorias: [
    { id: "cursos", subtitulo: "Cursos, faculdades e cursinhos", titulo: "Estude e prepare-se para o <span class=\"span\">futuro</span>" },
    { id: "emprego", subtitulo: "Estágio, emprego e Jovem Aprendiz", titulo: "Dê o primeiro passo na <span class=\"span\">carreira</span>" },
    { id: "idiomas", subtitulo: "Idiomas", titulo: "Aprenda um novo <span class=\"span\">idioma</span>" },
    { id: "intercambio", subtitulo: "Intercâmbio", titulo: "Viva uma experiência <span class=\"span\">internacional</span>" }
  ],

  itens: {

    cursos: [
      {
        tipo: "Prova",
        titulo: "Enem",
        descricao: "A nota do exame dá acesso ao Sisu, ao ProUni e ao Fies. A edição 2026 tem provas em 8 e 15 de novembro, e há isenção da taxa para quem se enquadra nos critérios.",
        local: "Todo o Brasil",
        link: "https://www.gov.br/inep/pt-br",
        imagem: "./assets/images/course-1.jpg"
      },
      {
        tipo: "Bolsa",
        titulo: "ProUni",
        descricao: "Bolsas integrais e parciais em faculdades particulares para quem fez o Enem e atende aos critérios de renda do programa.",
        local: "Todo o Brasil",
        link: "https://acessounico.mec.gov.br/prouni",
        imagem: "./assets/images/course-2.jpg"
      },
      {
        tipo: "Faculdade pública",
        titulo: "Sisu",
        descricao: "Sistema que usa a nota do Enem para distribuir vagas em universidades e institutos federais públicos, com cotas para diferentes perfis.",
        local: "Todo o Brasil",
        link: "https://acessounico.mec.gov.br/sisu",
        imagem: "./assets/images/course-3.jpg"
      },
      {
        tipo: "Financiamento",
        titulo: "Fies",
        descricao: "Financiamento estudantil para cursar graduação em faculdades particulares. O Fies Social reserva vagas para famílias de baixa renda inscritas no CadÚnico.",
        local: "Todo o Brasil",
        link: "https://acessounico.mec.gov.br/fies",
        imagem: "./assets/images/about-banner.jpg"
      },
      {
        tipo: "Cursinho",
        titulo: "Cursinho Popular da Poli-USP",
        descricao: "Preparatório para vestibulares e Enem mantido por estudantes da Poli-USP. Confira datas, valores e edital no site oficial.",
        local: "São Paulo",
        link: "https://cursinhopoliusp.com.br",
        imagem: "./assets/images/blog-1.jpg"
      },
      {
        tipo: "Cursinho",
        titulo: "Rede Nacional de Cursinhos Populares (CPOP)",
        descricao: "Iniciativa do MEC que reúne mais de 1,5 mil cursinhos populares em todo o país, com preparação gratuita para o Enem para estudantes de baixa renda.",
        local: "Todo o Brasil",
        link: "https://www.gov.br/mec/pt-br",
        imagem: "./assets/images/blog-2.jpg"
      },
      {
        tipo: "Curso online",
        titulo: "Escola Virtual.Gov",
        descricao: "Cursos online gratuitos, com certificado, em várias áreas. Você estuda no seu ritmo, pelo computador ou pelo celular.",
        local: "Online",
        link: "https://www.escolavirtual.gov.br",
        imagem: "./assets/images/blog-3.jpg"
      },
      {
        tipo: "Curso online",
        titulo: "Fundação Bradesco - Escola Virtual",
        descricao: "Cursos gratuitos de tecnologia, finanças, gestão e desenvolvimento pessoal, com certificado de conclusão.",
        local: "Online",
        link: "https://www.ev.org.br",
        imagem: "./assets/images/hero-banner-2.jpg"
      }
    ],

    emprego: [
      {
        tipo: "Estágio",
        titulo: "CIEE",
        descricao: "Cadastre seu currículo e concorra a vagas de estágio para estudantes do ensino médio, técnico e superior.",
        local: "Todo o Brasil",
        link: "https://www.ciee.org.br",
        imagem: "./assets/images/course-1.jpg"
      },
      {
        tipo: "Jovem Aprendiz",
        titulo: "Programa Jovem Aprendiz",
        descricao: "Contrato de aprendizagem para jovens de 14 a 24 anos, que une trabalho remunerado e formação profissional. Saiba como funciona no site do governo.",
        local: "Todo o Brasil",
        link: "https://www.gov.br/trabalho-e-emprego/pt-br",
        imagem: "./assets/images/hero-banner-1.jpg"
      },
      {
        tipo: "Estágio",
        titulo: "Nube",
        descricao: "Plataforma de estágio e trainee com vagas em empresas de todo o país e conteúdos para ajudar na preparação para os processos seletivos.",
        local: "Todo o Brasil",
        link: "https://www.nube.com.br",
        imagem: "./assets/images/course-3.jpg"
      }
    ],

    idiomas: [
      {
        tipo: "Inglês gratuito",
        titulo: "Inglês gratuito nos Institutos Federais",
        descricao: "O IFSP abre turmas gratuitas de inglês a distância ao longo do ano. Acompanhe os editais no site do instituto.",
        local: "Online",
        link: "https://www.ifsp.edu.br",
        imagem: "./assets/images/course-3.jpg"
      },
      {
        tipo: "Inglês gratuito",
        titulo: "Access to American Innovation",
        descricao: "Curso online gratuito de inglês para o mercado de trabalho, com foco em tecnologia e empreendedorismo, oferecido pela Embaixada dos EUA. A turma de 2026 já encerrou as inscrições, mas vale acompanhar novas edições.",
        local: "Online",
        link: "https://www.correio24horas.com.br/brasil/eua-oferecem-155-vagas-para-curso-de-ingles-gratuito-com-foco-em-tecnologia-e-empreendedorismo-0726",
        imagem: "./assets/images/blog-1.jpg"
      },
      {
        tipo: "App gratuito",
        titulo: "Duolingo",
        descricao: "Aplicativo gratuito para aprender inglês, espanhol e outros idiomas com lições curtas, no celular ou no computador.",
        local: "Online",
        link: "https://www.duolingo.com",
        imagem: "./assets/images/hero-banner-1.jpg"
      },
      {
        tipo: "Material gratuito",
        titulo: "LearnEnglish (British Council)",
        descricao: "Jogos, vídeos, gramática e exercícios gratuitos para praticar inglês em diferentes níveis.",
        local: "Online",
        link: "https://learnenglish.britishcouncil.org",
        imagem: "./assets/images/blog-2.jpg"
      }
    ],

    intercambio: [
      {
        tipo: "Bolsa integral",
        titulo: "Intercâmbio gratuito do Governo de SP",
        descricao: "Alunos da rede estadual estudam três meses no exterior, com despesas cobertas. A seleção começa no 9º ano, com base no desempenho no Saresp.",
        local: "São Paulo",
        link: "https://www.bnewssaopaulo.com.br/noticias/politica/veja-como-se-inscrever-no-programa-de-intercambio-gratuito-do-governo-de-sp.html",
        imagem: "./assets/images/hero-banner-1.jpg"
      },
      {
        tipo: "Bolsa integral",
        titulo: "Intercâmbio Cultural do Centro Paula Souza",
        descricao: "Alunos de Etecs e Fatecs podem ganhar bolsa para um intercâmbio de quatro semanas, com curso intensivo de inglês ou espanhol. As inscrições abrem em períodos específicos.",
        local: "São Paulo",
        link: "https://viva.com.br/carreira-e-educacao/centro-paula-souza-intercambio-cultural-gratuito-para-estudantes.html",
        imagem: "./assets/images/about-banner.jpg"
      },
      {
        tipo: "Bolsa integral",
        titulo: "Passaporte Mineiro do Conhecimento",
        descricao: "Programa do Governo de Minas com bolsas de intercâmbio para estudantes do 1º ano do Ensino Médio em Tempo Integral da rede estadual.",
        local: "Minas Gerais",
        link: "https://www.agenciaminas.mg.gov.br/news/pdf/125792.pdf",
        imagem: "./assets/images/blog-3.jpg"
      },
      {
        tipo: "Bolsa integral",
        titulo: "Maranhão Sem Fronteiras",
        descricao: "Bolsas de intercâmbio com todas as despesas pagas para estudantes do ensino médio da rede estadual do Maranhão, com destinos como Canadá e Argentina.",
        local: "Maranhão",
        link: "https://oimparcial.com.br/noticias/2026/05/governo-do-maranhao-oferece-100-bolsas-de-intercambio-no-canada-e-argentina/",
        imagem: "./assets/images/course-2.jpg"
      }
    ]

  }
};
