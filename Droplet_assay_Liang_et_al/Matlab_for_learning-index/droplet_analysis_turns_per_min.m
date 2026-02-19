% DROPLET ASSAY ANALYSIS
% He Liu for single worm , counting turns and speed, --20170315

%% load image 
button = length(questdlg('Load new data?','','Yes (JPG)','Yes (MAT) ','No', 'Yes (JPG)') ) ;
if button == 10
    clear all;
    [filename,pathname]  = uigetfile({'*.mat'});
    load([pathname filename]);
elseif button == 9
    clear all;
    [filename,pathname]  = uigetfile({'*.jpg'}, 'Select one image file');
    fname = [pathname filename(1:end-10)];
    answer = inputdlg({'Start frame', 'End frame'}, [pathname filename], 1,{['1'],['1200']});
    istart = str2num(answer{1});
    iend = str2num(answer{2});
    numframes = iend - istart + 1;

    i = istart ;
    fname2=strcat(fname, num2str(i, '%06d'), '.jpg');
    img = single(imread(fname2)); 
    [ysize xsize ] = size(img);
end
    %% select cropping for multiple worms

%     numroi = 2;
    answer = inputdlg('Number of ROIs','Number of ROIs',1,{'2'});
    numroi = str2num(answer{1});

    cropx1 = zeros(numroi,1);
    cropy1 = zeros(numroi,1);
    cropx2 = zeros(numroi,1);
    cropy2 = zeros(numroi,1);

    ignore_worm = zeros(numroi,1);
    
    for k=numroi:-1:1
    i=istart;
    fname2=strcat(fname, num2str(i, '%06d'), '.jpg');
    %       fname2=strcat(fname, num2str(i, '%03d'), '.jpg');
    img = single(imread(fname2)); 
    figure(1);clf;
    imagesc(img, [0 max(max(img))]); colormap spring; hold on;
    title(['worm #' num2str(k) ' select ROI: upper left then lower right or press enter to ignore']);
    tmp = ginput(1);
    if length(tmp)<2
       ignore_worm(k)=1;
       text(20,20,['Ignoring worm #' num2str(k)], 'Color', 'w');
%             pause(1);
    else
        ignore_worm(k)=0;
        cropx1(k)= floor(tmp(1));
        cropy1(k)  = floor(tmp(2));
        plot([1 xsize], [cropy1(k) cropy1(k)], '-b');
        plot([cropx1(k) cropx1(k)], [1 ysize], '-b');
        [cropx2(k) cropy2(k) ] = ginput(1);
        cropx2(k) = floor(cropx2(k));
        cropy2(k) = floor(cropy2(k));
        plot([1 xsize], [cropy2(k) cropy2(k)], '-b');
        plot([cropx2(k) cropx2(k)], [1 ysize], '-b');
        text(20,20,['worm #' num2str(k)], 'Color', 'w');
        pause(.1);
    end
    end
        %% FIND MINIMUM IMG %%%%%%
    figure(1); clf;
    axis image;
    title('minimum image');
    imgmin = 255*ones(size(img));
    numframes = iend - istart + 1;
    skip = round(numframes/10); 
    close
    for i=istart:skip:iend
    %     i = istart + (j - 1);
        fname2=strcat(fname, num2str(i, '%06d'), '.jpg');
    %       fname2=strcat(fname, num2str(i, '%03d'), '.jpg');
        img = single(imread(fname2)); 
        imgmin = min(img,imgmin);

        imagesc(imgmin); hold on;
        title('minimum image');
    %     title(num2str(i));
%         pause(0.1);
    end
    imgmin_thresh = 10;
    imgmin_bw = (imgmin > imgmin_thresh);
    se = strel('ball',3,3);

    imgmin_dilate = single(imdilate(imgmin,se)); 
    
    
        %%%%%%%%%%%%%%%%%%%%%%%%%%% MAIN CALCULATIONS %%%%%%%%%%%%%%%%%%%%%%%%%%%%
    numframes = iend-istart + 1;
    mask_multiplier = 1.1;
    img_threshold =  0.1;
    do_showimg = 0;
    showimg_multiple = 100;

    bw_Area = zeros(numroi, numframes);
    bw_Centroid = zeros(numroi, numframes,2);
    bw_Centroid_r = zeros(numroi, numframes);
    bw_Eccentricity = zeros(numroi, numframes);

    % figure(2);
    k0 = 2;  % worm to display.  0 for no display.

    fil = fspecial('disk', 5);
    % fspecial('gaussian', 10, 5);
    % se = strel('ball',5,5);
    if do_showimg
        figure(2); clf;
    end
    close
    h = waitbar(0,'Please wait...');
    tic
    for j=numframes:-1:1 
        
        steps = numframes;
        % computations take place here
        waitbar((numframes-j) / steps)
        
        
        i = istart + (j - 1);
        fname2=strcat(fname, num2str(i, '%06d'), '.jpg'); 
        img = single(imread(fname2));   % load image
        img = img - mask_multiplier*imgmin_dilate; % subtract background
        img(img<0)=0;  % set negative pixels to zero

         for k=numroi:-1:1 %change
            if ~ignore_worm(k)
            imgcrop = img(cropy1(k):cropy2(k),cropx1(k):cropx2(k));
%             colormap gray;
                masksize = min([80, cropy2(k)-cropy1(k), cropx2(k) - cropx1(k)]);
                tmp = zeros(size(imgcrop));
                tmp(1:masksize,1:masksize) = hann(masksize) * hann(masksize)';
                mask2 = circshift(tmp, [round(-masksize/2), round(-masksize/2)]);
            imgcrop1 = imfilter(imgcrop, fil, 'same');
            imgmax = max(max(imgcrop1));
            [yi xi] = find(imgcrop1 == imgmax,1);
            imgcrop1f = imgcrop1 .* circshift(mask2, [yi, xi]);
            imgcrop2 = imgcrop .* circshift(mask2, [yi, xi]);
            imgcrop1f_bw = (imgcrop1f>imgmax*img_threshold);
            imgcrop1f_bws = bwselect(imgcrop1f_bw,xi,yi,8);
            if do_showimg && mod(j,showimg_multiple)==1
                [ii jj] = ind2sub([3,4], k);
                p = sub2ind([4,3], jj, ii);
%                 subplot(3,4,p);
%                 imagesc(imgcrop1f_bws); hold on; colormap gray;
%                 plot(xi, yi, 'or');
%                 axis off;
%                 if k==1
%                     title(num2str(j));
%                 end
            end
            STATS = regionprops(bwlabel(imgcrop1f_bws), 'Area', 'Centroid', 'Eccentricity');
            bw_Area(k,j) = STATS.Area;
            bw_Centroid(k,j,:) = STATS.Centroid;
            bw_Eccentricity(k,j) = STATS.Eccentricity;
%             pause(0.1);
        end
        end
    end
    toc

close(h) 
%% %%%%%%%%%%%%%%%%%%%%%%%%% detect turns %%%%%%%%%%%%%%%%%%%%%%%%

do_pause = 0;  % pause after each ROI analysis?
    Eccentricity_filsize=3;  % filter size for smoothing eccentricity 
    Area_filsize = 10; % filter size for smoothing Area 
    Centroid_filsize = 10; % filter size for smoothing Centroid 
    
    peak_det_abs_threshold = 0.85;  %  absolute threshold for turn detection 
    peak_det_threshold = 0.15;  % minimum size of peak in eccentricity
    
    Centroid_r_threshold = .7;  % lower = more strict
    area_threshold =0.7;  % higher = more strict

    answer = inputdlg({'peak_det_abs_threshold', 'peak_det_threshold', 'Centroid_r_threshold', 'area_threshold' }, 'Parameters', 1,...
            {num2str(peak_det_abs_threshold),num2str(peak_det_threshold),num2str(Centroid_r_threshold), num2str(area_threshold)});
    peak_det_abs_threshold = str2num(answer{1});
    peak_det_threshold = str2num(answer{2});
    Centroid_r_threshold = str2num(answer{3});
    area_threshold = str2num(answer{4});
    
    bw_Centroid_r_filtered = zeros(numroi,numframes);
    bw_Eccentricity_filtered = zeros(numroi,numframes);
    bw_Area_filtered = zeros(numroi,numframes);
    droplet_radius = zeros(numroi,numframes);
    
    for kk=1:numroi  % Smoothing
        tmp1 = size(imgcrop2,1)/2 * ones(1,numframes);
        tmp2 = size(imgcrop2,2)/2 * ones(1,numframes);
        droplet_radius(kk) = (size(imgcrop2,1)+ size(imgcrop2,2))/4;
        bw_Centroid_r(kk,:) = ((bw_Centroid(kk,:,1)-tmp2).^2 + ((bw_Centroid(kk,:,2)-tmp1)).^2).^0.5/droplet_radius(kk);
        bw_Centroid_r_filtered(kk,:) = smooth(bw_Centroid_r(kk,:), Centroid_filsize);
        bw_Eccentricity_filtered(kk,:) = smooth(bw_Eccentricity(kk,:), Eccentricity_filsize);
        bw_Area_filtered(kk,:) = smooth(bw_Area(kk,:), Area_filsize);
        mean_Area(kk) = mean(bw_Area(kk,:));
        median_Area(kk) = median(bw_Area(kk,:));
    end


    turndata = zeros(numroi, numframes);
    data_invalid = zeros(numroi, numframes);
    turndata_valid = zeros(numroi, numframes);
    framrate=600; % per min
    time=(numframes/framrate);
for k=1:numroi  % detect turns
        if ignore_worm(k)
            data_invalid(k,:)=1;
        else
            [maxtab mintab] = peakdet(bw_Eccentricity_filtered(k,:),peak_det_threshold);
            headbending_threshold=0.02;
            [maxhead minhead] = peakdet(bw_Eccentricity(k,:),headbending_threshold);
            if size(mintab,1) > 0
            flag = zeros(size(mintab,1));
                for t=1:size(mintab,1)
                     if bw_Eccentricity_filtered(k,mintab(t,1)) < peak_det_abs_threshold
                         turndata(k,mintab(t,1))=1;
                     end
                end
            end

            data_invalid(k,:) = data_invalid(k,:) | (bw_Centroid_r_filtered(k,:)> Centroid_r_threshold);
            data_invalid(k,:) = data_invalid(k,:) | (bw_Area_filtered(k,:) < area_threshold* median_Area(k));

            turndata_valid(k,:) = turndata(k,:) .* ~data_invalid(k,:);

            if do_pause 
               pause; 
            end
        end
        for i=1:time
            headbending(i,k)=sum((minhead(:,1)>=(600*i-600))&(minhead(:,1)<600*i));
            if isempty(mintab);
                turn(i,k)=0;
            else
                turn(i,k)=sum((mintab(:,1)>=(600*i-600))&(mintab(:,1)<600*i));
            end
       end
end


% figure
% hold on
% plot(bw_Eccentricity)
% plot(maxhead(:,1),maxhead(:,2),'*')
% plot(minhead(:,1),minhead(:,2),'*')
% hold off 
% speed_headbending=(size(minhead,1))/(numframes/framrate);
% (size(maxhead,1)+size(minhead,1))  


% for j=1:numroi
% for i=1:time
%     headbending(i,j)=sum((minhead(:,j)>=(300*i-300))&(minhead(:,j)<300*i));
%     if isempty(mintab);
%         turn(i,j)=0;
%     else
%     turn(i,j)=sum((mintab(:,j)>=(300*i-300))&(mintab(:,j)<300*i));
%     end
% end
% end
        

savename01=[pathname,'\headbending.xlsx'];
% A = {'headbendings in 30sec','turns in 30sec';};
xlswrite(savename01,[headbending])
savename02=[pathname,'\turn.xlsx'];
% A = {'headbendings in 30sec','turns in 30sec';};
xlswrite(savename02,[turn])
[headbending turn]
% T=table(['headbendings in 30sec','turns in 30sec'],[headbending,turn])
msgbox('Data saved successfully')
