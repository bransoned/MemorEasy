<!-- Improved compatibility of back to top link: See: https://github.com/othneildrew/Best-README-Template/pull/73 -->
<a id="readme-top"></a>
<!--
*** Thanks for checking out the Best-README-Template. If you have a suggestion
*** that would make this better, please fork the repo and create a pull request
*** or simply open an issue with the tag "enhancement".
*** Don't forget to give the project a star!
*** Thanks again! Now go create something AMAZING! :D
-->



<!-- PROJECT SHIELDS -->
<!--
*** I'm using markdown "reference style" links for readability.
*** Reference links are enclosed in brackets [ ] instead of parentheses ( ).
*** See the bottom of this document for the declaration of the reference variables
*** for contributors-url, forks-url, etc. This is an optional, concise syntax you may use.
*** https://www.markdownguide.org/basic-syntax/#reference-style-links
-->
[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![project_license][license-shield]][license-url]
[![LinkedIn][linkedin-shield]][linkedin-url]



<!-- PROJECT LOGO -->
<br />
<div align="center">
  <a href="https://github.com/bransoned/Memory-Exporter">
    <img src="images/memory_exporter_logo.jpg" alt="Logo" width="128" height="128">
  </a>

<h3 align="center">Memory Exporter</h3>

  <p align="center">
    Python tool used to download Snapchat memory exports. This script allows you to extract and apply date, time, and location data to Snapchat memory exports EXIF data.
    <br />
    <a href="https://github.com/bransoned/Memory-Exporter"><strong>Explore the docs »</strong></a>
    <br />
    <br />
<!--    <a href="https://github.com/bransoned/Memory-Exporter">View Demo</a>
    &middot; -->
    <a href="https://github.com/bransoned/Memory-Exporter/issues/new?labels=bug&template=bug-report---.md">Report Bug</a>
    &middot;
    <a href="https://github.com/bransoned/Memory-Exporter/issues/new?labels=enhancement&template=feature-request---.md">Request Feature</a>
  </p>
</div>



<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
      <ul>
        <li><a href="#built-with">Built With</a></li>
      </ul>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Installation</a></li>
      </ul>
    </li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#roadmap">Roadmap</a></li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
    <li><a href="#acknowledgments">Acknowledgments</a></li>
  </ol>
</details>



<!-- ABOUT THE PROJECT -->
## About The Project

[![Product Name Screen Shot][product-screenshot]](https://example.com)

This project is intended to provide a simplified and better implemented approach for exporting Snapchat memories compared to the system provided by Snapchat and their Javascript implementation.

When using Memory Exporter, you can rapidly download your Memories, while also tagging them with their relevant EXIF data, which Snapchat does not provide. Likewise, the script also saves files with relevant date/time file names instead of SID values.
<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!--
### Built With
TODO Add built with images
* [![Next][Next.js]][Next-url]
* [![React][React.js]][React-url]
* [![Vue][Vue.js]][Vue-url]
* [![Angular][Angular.io]][Angular-url]
* [![Svelte][Svelte.dev]][Svelte-url]
* [![Laravel][Laravel.com]][Laravel-url]
* [![Bootstrap][Bootstrap.com]][Bootstrap-url]
* [![JQuery][JQuery.com]][JQuery-url]

<p align="right">(<a href="#readme-top">back to top</a>)</p>
-->


<!-- GETTING STARTED -->
## Getting Started

Below are steps needed to retrieve your Memories_history.html file from Snapchat and then how to install and use this file with Memory Exporter.

### Prerequisites

<!--This is an example of how to list things you need to use the software and how to install them.
* npm
  ```sh
  npm install npm@latest -g
  ```
-->

1. [Download your Memories data from Snapchat.](https://help.snapchat.com/hc/en-us/articles/7012305371156-How-do-I-download-my-data-from-Snapchat)
    - When asked which data you would like, only selecting Memories is required for this project, but you may select more data if you wish.
    - Ensure that your data range you want selected is correct. We recommend toggle date selection off to query all Memories on your account.
    - **Note**: This will not export your My Eyes Only folder. This must be done manually in the app.
    - Lastly, when delivered the zip file from Snapchat with your data, unzip and find the "memories_history.html" file. We will use this file in the script.
    - TODO Add images or a GIF showing process of selecting data.
2. Confirm that [Python](https://www.python.org/downloads/) is installed on your system.

### Installation

1. Clone and enter the repo
   ```sh
   git clone https://github.com/bransoned/Memory-Exporter.git
   cd Memory-Exporter
   ```
2. Create and source a virtual environment (skip this step if you already have a virtual environment you would like to use)
    ```sh
    python3 -m venv .venv
    source .venv/bin/activate
    ```
3. Install the required libraries
    ```sh
    pip3 install -r requirements.txt
    ```
4. Copy your "memories_history.html" file into the top level of the project directory
<p align="right">(<a href="#readme-top">back to top</a>)</p>

### Running the Script
1. Once the required libraries and user-specific memory file are installed and copied into the directory, you can run the script
    ```sh
    python3 script.py
    ```
    - The script will give output tracking the progress of the downloads. If exporting many memories, this may take some time.

<!-- USAGE EXAMPLES -->
## Usage

TODO: Use this space to show useful examples of how a project can be used. Additional screenshots, code examples and demos work well in this space. You may also link to more resources.

_For more examples, please refer to the [Documentation](https://example.com)_

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- ROADMAP -->
## Roadmap

- [ ] Edit EXIF data for JPGs and MP4 files.
- [ ] Edit EXIF data for JPGs or MP4s that are downloaded in a ZIP file.
- [ ] Remove ZIP files and combine their PNG layers with the parent PNG or MP4. Add relevant EXIF data when needed.
- [ ] Provide a GUI interface for ease of use by non-power users.
- [ ] Develop a package/executable for ease of portability to non-power users.

See the [open issues](https://github.com/bransoned/Memory-Exporter/issues) for a full list of proposed features (and known issues).

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- CONTRIBUTING -->
## Contributing

Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

If you have a suggestion that would make this better, please fork the repo and create a pull request. You can also simply open an issue with the tag "enhancement".
Don't forget to give the project a star! Thanks again!

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

If you do not feel comfortable contributing code to the project, you can also leave feedback in the Issues or Discussion sections.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

### Top contributors:

<a href="https://github.com/bransoned/Memory-Exporter/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=bransoned/Memory-Exporter" alt="contrib.rocks image" />
</a>



<!-- LICENSE -->
## License

Distributed under the AGPL-3.0 license. See `LICENSE.txt` for more information.

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- CONTACT -->
## Contact

Bransoned - [Discord](https://discord.com/users/b.ranson)

Project Link: [https://github.com/bransoned/Memory-Exporter](https://github.com/bransoned/Memory-Exporter)

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- ACKNOWLEDGMENTS -->
## Acknowledgments

* [] This is a personal project intended for my use-cases. I feel that others may be able to benefit from this tool, so I would like to share it along with the development process with others.

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->
[contributors-shield]: https://img.shields.io/github/contributors/bransoned/Memory-Exporter.svg?style=for-the-badge
[contributors-url]: https://github.com/bransoned/Memory-Exporter/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/bransoned/Memory-Exporter.svg?style=for-the-badge
[forks-url]: https://github.com/bransoned/Memory-Exporter/network/members
[stars-shield]: https://img.shields.io/github/stars/bransoned/Memory-Exporter.svg?style=for-the-badge
[stars-url]: https://github.com/bransoned/Memory-Exporter/stargazers
[issues-shield]: https://img.shields.io/github/issues/bransoned/Memory-Exporter.svg?style=for-the-badge
[issues-url]: https://github.com/bransoned/Memory-Exporter/issues
[license-shield]: https://img.shields.io/github/license/bransoned/Memory-Exporter.svg?style=for-the-badge
[license-url]: https://github.com/bransoned/Memory-Exporter/blob/master/LICENSE.txt
[linkedin-shield]: https://img.shields.io/badge/-LinkedIn-black.svg?style=for-the-badge&logo=linkedin&colorB=555
[linkedin-url]: https://linkedin.com/in/linkedin_username
[product-screenshot]: images/screenshot.png


<!-- Shields.io badges. You can a comprehensive list with many more badges at: https://github.com/inttter/md-badges -->
<!--
[Next.js]: https://img.shields.io/badge/next.js-000000?style=for-the-badge&logo=nextdotjs&logoColor=white
[Next-url]: https://nextjs.org/
[React.js]: https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB
[React-url]: https://reactjs.org/
[Vue.js]: https://img.shields.io/badge/Vue.js-35495E?style=for-the-badge&logo=vuedotjs&logoColor=4FC08D
[Vue-url]: https://vuejs.org/
[Angular.io]: https://img.shields.io/badge/Angular-DD0031?style=for-the-badge&logo=angular&logoColor=white
[Angular-url]: https://angular.io/
[Svelte.dev]: https://img.shields.io/badge/Svelte-4A4A55?style=for-the-badge&logo=svelte&logoColor=FF3E00
[Svelte-url]: https://svelte.dev/
[Laravel.com]: https://img.shields.io/badge/Laravel-FF2D20?style=for-the-badge&logo=laravel&logoColor=white
[Laravel-url]: https://laravel.com
[Bootstrap.com]: https://img.shields.io/badge/Bootstrap-563D7C?style=for-the-badge&logo=bootstrap&logoColor=white
[Bootstrap-url]: https://getbootstrap.com
[JQuery.com]: https://img.shields.io/badge/jQuery-0769AD?style=for-the-badge&logo=jquery&logoColor=white
[JQuery-url]: https://jquery.com -->
